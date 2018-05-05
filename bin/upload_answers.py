import os
import pandas as pd
import argparse

from src.codit_api_demo import CoditAPI

parser = argparse.ArgumentParser('Script to add Answers with their respective codes to survey from Excel.'\
                                 'Requires setting credentials to codit.co via the environment variables CODIT_EMAIL and'\
                                 'CODIT_PW.')
parser.add_argument('--xls', type=str, help='Excel file to parse answers from')
parser.add_argument('--sheet_number', default=0, type=int, help='Sheet number to parse in Excel file (starting from 0)')
parser.add_argument('--text_col', type=str, help='Column name of the answers text in the Excel file')
parser.add_argument('--codes_substring', type=str, help='Substring of code-columns (sparse format).'\
                    'Example: Excel contains columns "Code_1", "Code_2", ...' \
                    'Parse these codes by setting --codes_substring="Code"')
parser.add_argument('--sourcelanguage_col', type=str, help='Source language column (optional),'\
                                                           ' language-tags need to be ISO tags')
parser.add_argument('--survey_id', type=int, help='ID of survey to append answers to')
parser.add_argument('--dry_run', action='store_true', help='If set, do not upload data but show what would be uploaded')
args = parser.parse_args()

# parse credentials from environment variables
email = os.environ['CODIT_EMAIL']
pw = os.environ['CODIT_PW']

survey_id = args.survey_id


if __name__ == '__main__':
    # login
    api = CoditAPI('en')
    login = api.login(email, pw)

    # read data
    df_in= pd.read_excel(args.xls, sheetname=args.sheet_number)
    print('Adding {} answers'.format(len(df_in)))

    # renaming columns, parsing codes and separating the auxillary-columns
    answer_cols = []
    df_in= df_in.rename(columns={args.text_col: 'text'})
    answer_cols.append('text')

    if args.sourcelanguage_col:
        df_in = df_in.rename(columns={args.sourcelanguage_col: 'source_language'})
        answer_cols.append('source_language')

    if args.codes_substring:
        codes_cols = [col for col in df_in.columns if args.codes_substring in col]
        df_in['codes'] = df_in[codes_cols].values.tolist()
        df_in['codes'] = df_in['codes'].apply(lambda x: [int(it) for it in x if not pd.isnull(it)])
        df_in['reviewed'] = True
        answer_cols.append('codes')
        answer_cols.append('reviewed')
        df_in = df_in.drop(codes_cols, axis=1)

    # all the other columns are auxillary columns
    auxillary_column_names = [col_name for col_name in df_in.columns if col_name not in answer_cols]
    auxillary_cols = df_in[auxillary_column_names]

    # preparing request data
    df_answers = df_in.drop(auxillary_cols, axis=1)
    answers = df_answers.to_dict(orient='records')
    data = []
    for i, textrow in enumerate(answers):
        textrow['auxiliary_columns'] = auxillary_cols.values[i].tolist()
        data.append(textrow)

    # add the answers using the api
    if args.dry_run:
        print('Adding the following answers: ',data)
    else:
        new_answers = api.addAnswersToSurvey(survey_id, answers)
        if new_answers is not False:
            print("Added {} new answers to survey {}".format(len(new_answers), survey_id))
        else:
            print('error', new_answers)
