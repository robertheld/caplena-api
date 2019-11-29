import os
import numpy as np
import pandas as pd
import argparse
import re
from pprint import pprint
from PyInquirer import style_from_dict, Token, prompt
from PyInquirer import Validator, ValidationError
import getpass
import json
import time

from src.caplena_api_demo import CaplenaAPI

BATCH_SIZE = 2000

parser = argparse.ArgumentParser(
    description=
    'Script to create a new project with one question and their answers with codes from Excel or CSV \n'
)


class FileExistsValidator(Validator):
    def validate(self, document):
        ok = os.path.exists(document.text)
        if not ok:
            raise ValidationError(
                message='Please enter a valid file path', cursor_position=len(document.text)
            )  # Move cursor to end


class FileExistsOrNoneValidator(FileExistsValidator):
    def validate(self, document):
        if document.text:
            super(FileExistsOrNoneValidator, self).validate(document)


def parse_file(fp):
    if fp.endswith('.xlsx') or fp.endswith('.xls'):
        parse_fn = pd.read_excel
    elif fp.endswith('.csv'):
        parse_fn = pd.read_csv
    else:
        raise ValueError('Invalid file extension, please supplement a file with either .csv or .xlsx or .xls')
    try:
        df = parse_fn(fp)
        return df
    except Exception as e:
        print('ERROR, we couldnt read your file, please save it one more time and try again')
        exit()


if __name__ == "__main__":

    # PARSE INPUT
    question = [
        {
            'type': 'input',
            'name': 'filepath',
            'message':
            'Please enter the file path to the Excel file containing your codebook. If no codebook is available, hit enter',
            'validate': FileExistsOrNoneValidator
        }
    ]

    answers = prompt(question)

    codebook = []
    if answers['filepath']:
        df_codebook = parse_file(answers['filepath'])

        code_name_col = 'Code Name'
        code_category_col = 'Code Category'
        code_id_col = 'Code ID'
        for i, row in df_codebook.iterrows():
            code = {'id': row[code_id_col], 'label': row[code_name_col], 'category': row[code_category_col]}
            codebook.append(code)

        print('Successfully parsed codebook with {} codes'.format(len(codebook)))

    question = [
        {
            'type': 'input',
            'name': 'filepath',
            'message': 'Please enter the file path to the Excel file containing the answers',
            'validate': FileExistsValidator
        }
    ]

    answers = prompt(question)

    df_answers = parse_file(answers['filepath'])

    print('Found {} responses in provided file'.format(len(df_answers)))

    if codebook:
        codes_substring = 'CODE'
        codes_cols = [col for col in df_answers.columns if codes_substring in col]
        print('Discovered {} columns with codes'.format(len(codes_cols)))

    question = [
        {
            'type': 'input',
            'name': 'text_col',
            'message': 'Please enter the name of the column containing the text'
        }, {
            'type':
            'input',
            'name':
            'sourcelang_col',
            'message':
            'Please enter the name of the column containing the source language (ISO codes). Hit enter if not available.'
        }
    ]

    answers = prompt(question)

    text_col = answers['text_col']
    if text_col not in df_answers.columns:
        raise ValueError('Column {} does not exist'.format(text_col))
    sourcelang_col = answers['sourcelang_col']
    if sourcelang_col:
        if sourcelang_col not in df_answers.columns:
            raise ValueError('Column {} does not exist'.format(sourcelang_col))
        df_answers['source_language'] = df_answers[sourcelang_col]

    question = [
        {
            'type': 'confirm',
            'name': 'has_reviewed',
            'message': 'Do you have already coded rows?',
            'default': False
        }
    ]
    answers = prompt(question)
    if answers['has_reviewed']:
        question = [
            {
                'type': 'list',
                'choices': ['caplena.com_list', 'caplena.com_binary'],
                'name': 'codes_format',
                'message': 'In what format are the codes of the reviewed answers?',
                'default': 'caplena.com_list'
            }
        ]
        answers = prompt(question)

        codes_col = 'codes'
        if codebook:
            df_answers[codes_col] = df_answers[codes_cols].fillna(0).values.tolist()

            valid_code_ids = [code['id'] for code in codebook]

            def _check_if_code_exists(code_id):
                if not code_id in valid_code_ids:
                    raise ValueError(
                        'Code with ID {} was found in answers but not in Codebook'.format(code_id)
                    )
                else:
                    return code_id

            df_answers[codes_col] = df_answers[codes_col].apply(
                lambda x: [
                    _check_if_code_exists(int(it)) for it in x
                    if (not pd.isnull(it) and str(it).strip() and it != 0)
                ]
            )

        if answers['codes_format'] == 'caplena.com_binary':
            code_id_clean_regex = re.compile('Code ID ')
            code_name_clean_regex = re.compile('Code Name |\'')
            code_category_clean_regex = re.compile('Code category|\'')
            codes_cols = [col for col in df_answers.columns if len(col.split('|')) == 3]
            print('Found the following code columns: ', codes_cols)
            for i, code in enumerate(codes_cols):
                id, label, cat = code.split('|')
                id = int(code_id_clean_regex.sub('', id).strip())
                cat = code_category_clean_regex.sub('', cat).strip()
                label = code_name_clean_regex.sub('', label).strip()
                codebook.append({'label': label, 'category': cat.upper(), 'id': id})
            # The codes are in binary format, i.e. [0 0 1 0]
            from sklearn.preprocessing import MultiLabelBinarizer
            import numpy as np

            # Instantiate the binarizer
            binarizer = MultiLabelBinarizer()
            # Convert NAs to 0, concatenate columns to one list per row
            df_answers['codes'] = df_answers[codes_cols].fillna(0).values.tolist()
            # Prepare the binarizer: Our code IDs are 1:len(code_cols)
            binarizer.fit(np.asarray([[code['id'] for code in codebook]]))

            def codes_from_binary(row):
                row = [0 if el == ' ' else el for el in row]
                binary_mat = np.asarray([[int(el) for el in row]])
                return [int(res) for res in binarizer.inverse_transform(binary_mat)[0]]

            df_answers['codes'] = df_answers['codes'].apply(codes_from_binary)
            print('Parsed codebook from column names: ', codebook)

        elif answers['codes_format'] == 'caplena.com_list':
            codes_cols = [col for col in df_answers.columns if 'Code ID' in col]
            # The codes are in "list" format, i.e. for every row [code_id1, code_id2]
            # (different lengths for rows possible)
            df_answers[codes_col] = df_answers[codes_cols].values.tolist()
            df_answers[codes_col] = df_answers[codes_col].apply(
                lambda x: [int(it) for it in x if (not pd.isnull(it) and str(it).strip())]
            )
            code_name_and_cat_cols = [
                col for col in df_answers.columns
                if 'Code Name' in col or 'Code Kategorie' in col or 'Code Category' in col
            ]
            df_answers = df_answers.drop(code_name_and_cat_cols, axis=1)

        df_answers['reviewed'] = ~df_answers[codes_cols].isnull().all(1)
        answer_cols = [text_col, codes_cols, codes_col, 'reviewed', 'source_language']
        df_answers = df_answers.drop(codes_cols, axis=1)
    else:
        df_answers['reviewed'] = False
        answer_cols = [text_col, 'reviewed', 'source_language']

    auxiliary_col_names = [col_name for col_name in df_answers.columns if col_name not in answer_cols]
    print("Adding {} auxiliary columns: {}".format(len(auxiliary_col_names), auxiliary_col_names))

    # also fill NaN's in auxiliary columns
    auxiliary_cols = df_answers[auxiliary_col_names].fillna(value='')
    # Convert all non-numeric columns to strings (e.g. timestamps, datetime)
    for col_name in auxiliary_col_names:
        if not np.issubdtype(auxiliary_cols[col_name].dtype, np.number):
            auxiliary_cols[col_name] = auxiliary_cols[col_name].astype(str, copy=False)
    # Force conversion to string
    df_answers[text_col] = df_answers[text_col].astype(str, copy=False)
    df_answers = df_answers.rename(columns={text_col: 'text'})

    # preparing request data
    df_answers = df_answers.drop(auxiliary_cols, axis=1)
    df_answers['auxiliary_columns'] = auxiliary_cols.values.tolist()
    rows = []
    for i, answer in df_answers.iterrows():
        aux_column = answer.pop('auxiliary_columns')
        rows.append({'auxiliary_columns': aux_column, 'answers': [answer.to_dict()]})

    time.sleep(2)
    # parse credentials from environment variables
    email = os.environ.get('CAPLENA_EMAIL', None)
    pw = os.environ.get('CAPLENA_PW', None)

    # LOGIN
    print('Logging you in to Caplena.com')
    time.sleep(1)
    api = CaplenaAPI('en')

    if email is None:
        email = input('Enter your email: ')
    if pw is None:
        pw = getpass.getpass(prompt='Enter your password (not displayed): ')

    login = api.login(email, pw)
    print('Login successful')

    # UPLOAD
    question = [
        {
            'type': 'input',
            'name': 'project_name',
            'message': 'Please enter the name of the new project'
        },
        {
            'type': 'input',
            'name': 'language',
            'message':
            'Please enter the language of the new project (ISO code). If data is multilingual, enter the most prominent language',
            'default': 'en'
        },
    ]
    answers = prompt(question)
    project_name = answers['project_name']
    language = answers['language']
    new_questions = [{'name': text_col, 'codebook': codebook}]
    new_project = api.createProject(
        project_name,
        language=language,
        auxiliary_column_names=auxiliary_col_names,
        translate=False,
        questions=new_questions
    )
    if new_project is not False:
        print("Created new project with id {}".format(new_project['id']))

    project = new_project
    project_id = project['id']
    question_id = project['questions'][0]['id']
    for row in rows:
        row['answers'][0]['question'] = question_id
    print('Adding {} answers to question {} in project {}'.format(len(rows), question_id, project_id))
    # batch answers for large surveys in order not to hit the limit
    if len(rows) < BATCH_SIZE:
        new_answers = api.addRowsToProject(project_id, rows)
        if new_answers is not False:
            print("Added {} new answers to question {}".format(len(new_answers), question_id))
        else:
            print('error', new_answers)
    else:
        batch_number = 0
        j = 0
        while j < len(rows):
            print('Adding batch {}'.format(batch_number))
            min_idx = j
            max_idx = j + BATCH_SIZE
            new_answers = api.addRowsToProject(project_id, rows[min_idx:max_idx])
            j = max_idx
            if new_answers is not False:
                print(
                    "Added batch {} with {} new rows to question {}".format(
                        batch_number, len(new_answers), question_id
                    )
                )
            else:
                print('error on batch {}: {}'.format(batch_number, new_answers))
            batch_number += 1
