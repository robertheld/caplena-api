import os
from typing import Dict, List
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

from src.caplena_api_demo import CaplenaAPI, Project, Question, Answer, Row, Code

BATCH_SIZE = 2000

parser = argparse.ArgumentParser(
    description=
    'Script to create a new project with one question and their answers with codes from Excel or CSV \n'
)

CODES_COL = 'codes'


class FileExistsValidator(Validator):
    def validate(self, document):
        ok = os.path.exists(document.text)
        if not ok:
            raise ValidationError(
                message='Please enter a valid file path', cursor_position=len(document.text)
            )  # Move cursor to end


class ListFileExistsOrNoneValidator(Validator):
    def validate(self, document):
        if document.text:
            for fp in document.text.split(','):
                ok = os.path.exists(fp)
                if not ok:
                    raise ValidationError(
                        message='Please enter valid file paths', cursor_position=len(document.text)
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


def parse_codebook(filepath) -> List[Code]:
    """

    :param prompt_answers:
    :return:
    """
    df_codebook = parse_file(filepath)

    prompt_question = [
        {
            'type': 'input',
            'name': 'code_name_col',
            'message': 'Please enter the name of the column containing the code names',
            'default': 'Code Name'
        }, {
            'type': 'input',
            'name': 'cat_name_col',
            'message': 'Please enter the name of the column containing the category names, if your codebook'
            'does not contain categories, just enter none and we create a default category "CODES" for you',
            'default': 'Code Category'
        }, {
            'type': 'input',
            'name': 'code_id_col',
            'message': 'Please enter the name of the column containing the code id, if your codebook does not'
            'contain ids, just enter none and we create default code ids',
            'default': 'Code ID'
        }
    ]
    prompt_answers = prompt(prompt_question)
    code_name_col = prompt_answers['code_name_col']
    code_category_col = prompt_answers['cat_name_col']
    code_id_col = prompt_answers['code_id_col']
    codebook = []
    for i, row in df_codebook.iterrows():
        code_name = row[code_name_col]
        if pd.isna(code_name):
            print('WARNING: Empty code name in row {}, skipping'.format(i))
            continue
        if code_category_col:
            cat = row[code_category_col]
        else:
            cat = 'CODES'
        if code_id_col:
            code_id = row[code_id_col]
        else:
            code_id = i + 1
        code = Code(id=code_id, label=row[code_name_col], category=cat)
        codebook.append(code)
    print('Successfully parsed codebook with {} codes'.format(len(codebook)))
    return codebook


def parse_binary_codes_format(df_answers, codebook, codes_cols, codes_col='codes'):
    """
    Converts binary code format (i.e. [0 0 1 0]) to list (i.e. [3])
    :return:
    """
    # Convert NAs to 0, concatenate columns to one list per row
    df_answers[codes_col] = df_answers[codes_cols].fillna(0).values.tolist()
    code_ids = [code.id for code in codebook]

    def codes_from_binary(row):
        codes = [code_ids[i] for i, el in enumerate(row) if (isinstance(el, int) or el == 'x') and el != 0]
        return codes

    df_answers[codes_col] = df_answers[codes_col].apply(codes_from_binary)
    print('Parsed codebook from column names: ', codebook)
    return df_answers


def parse_list_codes_format(df_answers, code_id_substr: str, codebook: List[Code], codes_col='codes'):
    """
    parse list format, i.e. for every row [code_id1, code_id2] (different lengths for rows possible)
    :param df_answers:
    :param code_id_substr:
    :param codebook:
    :param codes_col:
    :return:
    """
    valid_code_ids = [code.id for code in codebook]

    def _check_if_code_exists(code_id):
        if not code_id in valid_code_ids:
            raise ValueError('Code with ID {} was found in answers but not in Codebook'.format(code_id))
        else:
            return code_id

    codes_cols = [col for col in df_answers.columns if code_id_substr in col]
    df_answers[codes_col] = df_answers[codes_cols].values.tolist()
    df_answers[codes_col] = df_answers[codes_col].apply(
        lambda x:
        [_check_if_code_exists(int(it)) for it in x if (not pd.isnull(it) and str(it).strip() and it != 0)]
    )
    return df_answers, codes_cols


def parse_reviewed(df_answers, codebook: List[Code]):
    """
    Parse reviewed responses
    :param df_answers:
    :return:
    """
    question = [
        {
            'type': 'list',
            'choices': ['caplena.com_list', 'caplena.com_binary', 'generic_binary', 'generic_list'],
            'name': 'codes_format',
            'message': 'In what format are the codes of the reviewed answers?',
            'default': 'caplena.com_list'
        }
    ]
    answers = prompt(question)

    if answers['codes_format'] == 'caplena.com_binary':
        # parse codebook from column names
        code_id_clean_regex = re.compile('Code ID ')
        code_name_clean_regex = re.compile('Code Name |\'')
        code_category_clean_regex = re.compile('Code Category|\'')
        codes_cols = [col for col in df_answers.columns if len(col.split('|')) == 3]
        print('Found the following code columns: ', codes_cols)
        for i, code_str in enumerate(codes_cols):
            id, label, cat = code_str.split('|')
            id = int(code_id_clean_regex.sub('', id).strip())
            cat = code_category_clean_regex.sub('', cat).strip()
            label = code_name_clean_regex.sub('', label).strip()
            codebook.append(Code(label=label, category=cat.upper(), id=id))
        df_answers = parse_binary_codes_format(df_answers, codebook, codes_cols, codes_col)
    elif answers['codes_format'] == 'generic_binary':
        question = [
            {
                'type':
                'input',
                'name':
                'start_idx',
                'message':
                'Please enter the index of the first column containing codes (index starts from 0, code columns are assumed to be contiguous)',
            }, {
                'type':
                'input',
                'name':
                'end_idx',
                'message':
                'Please enter the index of the last column containing codes (index starts from 0, code columns are assumed to be contiguous)',
            }
        ]
        answers = prompt(question)
        codes_cols = list(df_answers.columns[int(answers['start_idx']):int(answers['end_idx'])])
        print('Found the following code columns: ', codes_cols)
        for i, code_str in enumerate(codes_cols):
            codebook.append(Code(label=code_str, category='CODES', id=i))
        df_answers = parse_binary_codes_format(df_answers, codebook, codes_cols, CODES_COL)
    elif answers['codes_format'] == 'caplena.com_list':
        df_answers, codes_cols = parse_list_codes_format(
            df_answers, code_id_substr='Code ID', codebook=codebook
        )
        code_name_and_cat_cols = [
            col for col in df_answers.columns
            if 'Code Name' in col or 'Code Kategorie' in col or 'Code Category' in col
        ]
        df_answers = df_answers.drop(code_name_and_cat_cols, axis=1)
    elif answers['codes_format'] == 'generic_list':
        question = {
            'type':
            'input',
            'name':
            'code_substring',
            'message':
            'Please enter the substring that defines code columns (i.e. if your Code columns are "Code_1", "Code_2", etc. enter "Code").',
        }
        answers = prompt(question)
        df_answers, codes_cols = parse_list_codes_format(
            df_answers, code_id_substr=answers['code_substring'], codebook=codebook
        )
    else:
        raise ValueError('Invalid codes_format')
    df_answers['reviewed'] = ~df_answers[codes_cols].isnull().all(1)
    answer_cols = [text_col, codes_cols, CODES_COL, 'reviewed', 'source_language']
    df_answers = df_answers.drop(codes_cols, axis=1)
    return df_answers, answer_cols


def parse_reviewed_multi_question(df_answers, codebooks: List[List[Code]]):
    """
    Parse reviewed responses from multiple questions
    :param df_answers:
    :param codebooks:
    :return:
    """
    question = [
        {
            'type': 'list',
            'choices': ['generic_list'],
            'name': 'codes_format',
            'message': 'In what format are the codes of the reviewed answers?',
            'default': 'generic_list'
        }
    ]
    answers = prompt(question)
    if answers['codes_format'] == 'generic_list':
        question = {
            'type':
            'input',
            'name':
            'code_substrings',
            'message':
            'Please enter the substrings that defines code columns per question separated by "," in the same order as the codebooks (i.e. if your Code columns are "Code_1", "Code_2", etc. enter "Code").',
        }
        answers = prompt(question)
        code_id_substrings = answers['code_substrings'].split(',')
        all_code_cols = []
        code_col_names = []
        for i, (code_id_substr, codebook) in enumerate(zip(code_id_substrings, codebooks)):
            print('Parsing Codes with substring {}'.format(code_id_substr))
            df_answers, codes_cols = parse_list_codes_format(
                df_answers, code_id_substr=code_id_substr, codebook=codebook
            )
            all_code_cols.extend(codes_cols)
            code_col_name = '{}_{}'.format(CODES_COL, i)
            code_col_names.append(code_col_name)
            df_answers = df_answers.rename(columns={CODES_COL: code_col_name})
        df_answers['reviewed'] = ~df_answers[all_code_cols].isnull().all(1)
        answer_cols = [all_code_cols, *code_col_names, 'reviewed', 'source_language']
        df_answers = df_answers.drop(all_code_cols, axis=1)
    else:
        answer_cols = None
    return df_answers, answer_cols


if __name__ == "__main__":

    question = [
        {
            'type': 'confirm',
            'name': 'has_multi_questions',
            'message': 'Does your project have multiple open questions?'
        }
    ]
    has_multi_questions = prompt(question)['has_multi_questions']
    if not has_multi_questions:
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
        fp = answers.get('filepath')
        if fp:
            codebook = parse_codebook(fp)

        def parse_reviewed_fn(x):
            return parse_reviewed(x, codebook)
    else:
        question = [
            {
                'type': 'input',
                'name': 'filepaths',
                'message':
                'Please enter the file paths to the Excel file containing your codebooks separated by ",". If no codebook is available, hit enter',
                'validate': ListFileExistsOrNoneValidator
            }
        ]

        answers = prompt(question)

        codebooks = []
        fps = answers.get('filepaths')
        if fps:
            fps = fps.split(',')
            for fp in fps:
                print('Parsing codebook {}'.format(fp))
                codebook = parse_codebook(fp)
                codebooks.append(codebook)

        def parse_reviewed_fn(x):
            return parse_reviewed_multi_question(x, codebooks)

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

    if not has_multi_questions:
        question = [
            {
                'type': 'input',
                'name': 'text_col',
                'message': 'Please enter the name of the column containing the text'
            },
        ]

        answers = prompt(question)

        text_col = answers['text_col']
        if text_col not in df_answers.columns:
            raise ValueError('Column {} does not exist'.format(text_col))
        text_cols = [text_col]
    else:
        question = [
            {
                'type':
                'input',
                'name':
                'text_cols',
                'message':
                'Please enter the name of the columns containing the text separated by "," in the same order as the codebooks'
            },
        ]

        answers = prompt(question)

        text_cols = answers['text_cols'].split(',')
        for text_col in text_cols:
            if text_col not in df_answers.columns:
                raise ValueError('Column {} does not exist'.format(text_col))

    question = [
        {
            'type':
            'input',
            'name':
            'sourcelang_col',
            'message':
            'Please enter the name of the column containing the source language (ISO codes). Hit enter if not available.'
        }
    ]
    answers = prompt(question)
    sourcelang_col = answers['sourcelang_col']
    if sourcelang_col:
        if sourcelang_col not in df_answers.columns:
            raise ValueError('Column {} does not exist'.format(sourcelang_col))
        df_answers['source_language'] = df_answers[sourcelang_col].apply(lambda x: x.lower())

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
        df_answers, answer_cols = parse_reviewed_fn(df_answers)
        answer_cols.extend(text_cols)
    else:
        df_answers['reviewed'] = False
        answer_cols = [*text_cols, 'reviewed', 'source_language']
    auxiliary_col_names = [col_name for col_name in df_answers.columns if col_name not in answer_cols]
    print("Adding {} auxiliary columns: {}".format(len(auxiliary_col_names), auxiliary_col_names))

    # also fill NaN's in auxiliary columns
    auxiliary_cols = df_answers[auxiliary_col_names].fillna(value='')
    # Convert all non-numeric columns to strings (e.g. timestamps, datetime)
    for col_name in auxiliary_col_names:
        if not np.issubdtype(auxiliary_cols[col_name].dtype, np.number):
            auxiliary_cols[col_name] = auxiliary_cols[col_name].astype(str, copy=False)
    # Force conversion to string
    for text_col in text_cols:
        df_answers[text_col] = df_answers[text_col].apply(lambda x: '' if pd.isna(x) else x)
        df_answers[text_col] = df_answers[text_col].astype(str, copy=False)

    # preparing request data
    df_answers = df_answers.drop(auxiliary_cols, axis=1)
    df_answers['auxiliary_columns'] = auxiliary_cols.values.tolist()
    row_data = []
    for i, answer in df_answers.iterrows():
        aux_column = answer.pop('auxiliary_columns')
        if has_multi_questions:
            answers_up = []
            for j, text_col in enumerate(text_cols):
                code_col = '{}_{}'.format(CODES_COL, j)
                answer_up = {'text': answer[text_col], 'reviewed': answer['reviewed'], 'question': text_col}
                if 'codes' in answer.keys():
                    answer_up['codes'] = answer[code_col]
                if 'source_language' in answer.keys():
                    answer_up['source_language'] = answer['source_language']
                answers_up.append(answer_up)
        else:
            answers_up = [answer.to_dict()]
        row_data.append({'auxiliary_columns': aux_column, 'answers': answers_up})
    print(row_data[:10])
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
    if has_multi_questions:
        new_questions = []
        if len(codebooks) == 0:
            for text_col in text_cols:
                new_questions.append(Question(name=text_col, codebook=[]))
        for text_col, codebook in zip(text_cols, codebooks):
            print(text_col, codebook)
            new_questions.append(Question(name=text_col, codebook=codebook))
    else:
        new_questions = [Question(name=text_cols[0], codebook=codebook)]
    new_project = api.createProject(
        project_name,
        language=language,
        auxiliary_column_names=auxiliary_col_names,
        translate=False,
        questions=new_questions
    )
    if new_project is not False:
        print("Created new project with id {}".format(new_project.id))

    project = new_project
    project_id = project.id
    rows = []
    for dat in row_data:
        if not has_multi_questions:
            question_id = project.questions[0].id
            dat['answers'][0]['question'] = question_id
            rows.append(
                Row(
                    auxiliary_columns=dat['auxiliary_columns'], answers=[Answer.from_json(dat['answers'][0])]
                )
            )
        else:
            answers = []
            for ans_dat, question in zip(dat['answers'], new_project.questions):
                ans_dat['question'] = question.id
                ans = Answer.from_json(ans_dat)
                answers.append(ans)
            rows.append(Row(auxiliary_columns=dat['auxiliary_columns'], answers=answers))

    print('Adding {} answers to project {}'.format(len(rows), project_id))
    # batch answers for large surveys in order not to hit the limit
    if len(rows) < BATCH_SIZE:
        new_answers = api.addRowsToProject(project_id, rows)
        if new_answers is not False:
            print("Added {} new rows to project {}".format(len(new_answers), project_id))
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
                    "Added batch {} with {} new rows to project {}".format(
                        batch_number, len(new_answers), project_id
                    )
                )
            else:
                print('error on batch {}: {}'.format(batch_number, new_answers))
            batch_number += 1
