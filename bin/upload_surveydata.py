import os
import numpy as np
import pandas as pd
import argparse
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

        code_name_col = 'NAME'
        code_category_col = 'CATEGORY'
        code_id_col = 'CODE ID'
        for i, row in df_codebook.iterrows():
            code = {'id': row[code_id_col], 'label': row[code_name_col], 'category': row[code_category_col]}
            codebook.append(code)

        print('Successfully parsed codebook with {} codes'.format(len(codebook)))

    question = [
        {
            'type': 'input',
            'name': 'filepath',
            'message': 'Please enter the file path to the Excel file containing the coded answers',
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
        }
    ]

    answers = prompt(question)

    text_col = answers['text_col']
    if text_col not in df_answers.columns:
        raise ValueError('Column {} does not exist'.format(text_col))

    if codebook:
        codes_col = 'codes'
        df_answers[codes_col] = df_answers[codes_cols].fillna(0).values.tolist()

        valid_code_ids = [code['id'] for code in codebook]

        def _check_if_code_exists(code_id):
            if not code_id in valid_code_ids:
                raise ValueError('Code with ID {} was found in answers but not in Codebook'.format(code_id))
            else:
                return code_id

        df_answers[codes_col] = df_answers[codes_col].apply(
            lambda x: [
                _check_if_code_exists(int(it)) for it in x
                if (not pd.isnull(it) and str(it).strip() and it != 0)
            ]
        )

        # empty rows are not-reviewed, find them
        df_answers['reviewed'] = ~df_answers[codes_cols].isnull().all(1)
        answer_cols = [text_col, codes_cols, codes_col, 'reviewed']
        df_answers = df_answers.drop(codes_cols, axis=1)
    else:
        df_answers['reviewed'] = False
        answer_cols = [text_col, 'reviewed']

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
