import os
import argparse
from PyInquirer import style_from_dict, Token, prompt
from PyInquirer import Validator, ValidationError
import getpass
import time

from src.caplena_api_demo import CaplenaAPI

BATCH_SIZE = 2000

parser = argparse.ArgumentParser(
    description='Script to copy a new project along with all its corresponding data \n'
)

# parse credentials from environment variables
caplena_api_key = os.environ.get('CAPLENA_API_KEY')

# LOGIN
print('Logging you in to Caplena.com')
time.sleep(1)
api = CaplenaAPI('en', caplena_api_key)


class ProjectExistsValidator(Validator):
    def validate(self, document):
        project_id = document.text
        _ = api.getProject(project_id)


if __name__ == "__main__":

    prompt_question = [
        {
            'type': 'input',
            'name': 'project_id',
            'message': 'Please enter the project to be copied',
            'validate': ProjectExistsValidator
        },
    ]
    prompt_answers = prompt(prompt_question)
    proj = api.getProject(prompt_answers['project_id'])
    rows = api.listRows(prompt_answers['project_id'])
    print('Found project {} with {} rows and {} questions'.format(proj.name, len(rows), len(proj.questions)))
    # prepare data for copy
    question_names = [q.name for q in proj.questions]
    new_rows = rows
    for row in new_rows:
        for question_name, ans in zip(question_names, row.answers):
            ans.question = question_name
    new_questions = []
    for q in proj.questions:
        q.id = None
        new_questions.append(q)
    prompt_question = [
        {
            'type': 'input',
            'name': 'project_name',
            'message': 'Please enter the project name of the copy'
        },
    ]
    prompt_answers = prompt(prompt_question)
    # create project
    new_proj = api.createProject(
        name=prompt_answers['project_name'],
        language=proj.language,
        auxiliary_column_names=proj.auxiliary_column_names,
        translate=proj.translate,
        translation_engine=proj.translation_engine,
        questions=new_questions,
        rows=new_rows,
        upload_async=True
    )

    print('Successfully created copy {} with id {}'.format(new_proj.name, new_proj.id))
