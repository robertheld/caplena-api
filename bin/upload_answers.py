import os
import numpy as np
import pandas as pd
import argparse
import getpass

from src.codit_api_demo import CoditAPI

parser = argparse.ArgumentParser('Script to add Answers with their respective codes to survey from Excel.'\
                                 'Requires setting credentials to codit.co via the environment variables CODIT_EMAIL and'\
                                 'CODIT_PW.')
parser.add_argument('--xls', required=True, type=str, help='Excel file to parse answers from')
parser.add_argument(
    '--sheet-number', default=0, type=int, help='Sheet number to parse in Excel file (starting from 0)'
)
parser.add_argument(
    '--text-col', required=True, type=str, help='Column name of the answers text in the Excel file'
)
parser.add_argument('--codes-substring', required=True,type=str, help='Substring of code-columns (sparse format).'\
                    'Example: Excel contains columns "Code_1", "Code_2", ...' \
                    'Parse these codes by setting --codes-substring="Code"')
parser.add_argument('--sourcelanguage-col', type=str, help='Source language column (optional),'\
                                                           ' language-tags need to be ISO tags')
parser.add_argument('--survey-id', type=int, required=True, help='ID of survey to append answers to')
parser.add_argument(
    '--codes-binary',
    action='store_true',
    help=
    'If set, codes are expected to be in binary format. The code ids are assumed to be continuous and start from zero'
)
parser.add_argument(
    '--dry-run', action='store_true', help='If set, do not upload data but show what would be uploaded'
)
args = parser.parse_args()

# parse credentials from environment variables
email = os.environ.get('CODIT_EMAIL', None)
pw = os.environ.get('CODIT_PW', None)

survey_id = args.survey_id

if __name__ == '__main__':
    # read data
    df_in = pd.read_excel(args.xls, sheet_name=args.sheet_number)
    print('Adding {} answers'.format(len(df_in)))

    # renaming columns, parsing codes and separating the auxiliary-columns
    answer_cols = []

    if args.text_col not in df_in.columns:
        raise AttributeError('Text column doesn\'t exist: {}'.format(args.text_col))

    df_in = df_in.rename(columns={args.text_col: 'text'})
    df_in['text'].fillna(value='', inplace=True)
    answer_cols.append('text')

    if args.sourcelanguage_col:
        df_in = df_in.rename(columns={args.sourcelanguage_col: 'source_language'})
        answer_cols.append('source_language')

    if args.codes_substring:
        codes_cols = [col for col in df_in.columns if args.codes_substring in col]

        print("Discovered {} code columns".format(len(codes_cols)))

        if args.codes_binary:
            # The codes are in binary format, i.e. [0 0 1 0]
            from sklearn.preprocessing import MultiLabelBinarizer
            import numpy as np

            # Instantiate the binarizer
            binarizer = MultiLabelBinarizer()
            # Convert NAs to 0, concatenate columns to one list per row
            df_in['codes'] = df_in[codes_cols].fillna(0).values.tolist()
            # Prepare the binarizer: Our code IDs are 0:len(code_cols)-1
            binarizer.fit(np.asarray([range(len(codes_cols))]))

            def codes_from_binary(row):
                binary_mat = np.asarray([[int(el) for el in row]])
                return [int(res) for res in binarizer.inverse_transform(binary_mat)[0]]

            df_in['codes'] = df_in['codes'].apply(codes_from_binary)
        else:
            # The codes are in "list" format, i.e. for every row [code_id1, code_id2] (different lengths for rows possible)
            df_in['codes'] = df_in[codes_cols].values.tolist()
            df_in['codes'] = df_in['codes'].apply(lambda x: [int(it) for it in x if not pd.isnull(it)])
        df_in['reviewed'] = True
        answer_cols.append('codes')
        answer_cols.append('reviewed')
        df_in = df_in.drop(codes_cols, axis=1)

    # all the other columns are auxiliary columns
    auxiliary_col_names = [col_name for col_name in df_in.columns if col_name not in answer_cols]
    auxiliary_cols = df_in[auxiliary_col_names]

    print("Appending {} auxiliary columns: {}".format(len(auxiliary_col_names), auxiliary_col_names))

    # Convert all non-numeric columns to strings (e.g. timestamps, datetime)
    for col_name in auxiliary_col_names:
        if not np.issubdtype(auxiliary_cols[col_name].dtype, np.number):
            auxiliary_cols[col_name] = auxiliary_cols[col_name].astype(str, copy=False)

    # preparing request data
    df_answers = df_in.drop(auxiliary_cols, axis=1)
    answers = df_answers.to_dict(orient='records')
    data = []
    for i, textrow in enumerate(answers):
        textrow['auxiliary_columns'] = auxiliary_cols.values[i].tolist()
        data.append(textrow)

    # add the answers using the api
    if args.dry_run:
        print('Adding the following answers: ', data)
    else:
        # login
        api = CoditAPI('en')

        if email is None:
            email = input('Enter your email: ')
        if pw is None:
            pw = getpass.getpass(prompt='Enter your password (not displayed): ')

        login = api.login(email, pw)

        new_answers = api.addAnswersToSurvey(survey_id, answers)
        if new_answers is not False:
            print("Added {} new answers to survey {}".format(len(new_answers), survey_id))
        else:
            print('error', new_answers)
