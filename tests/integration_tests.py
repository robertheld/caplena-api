import os, time

import pytest

from src.codit_api_demo import CoditAPI


api = CoditAPI('en')

baseuri = os.environ.get('BASEURI')
codit_email = os.environ.get('CODIT_EMAIL')
codit_pw = os.environ.get('CODIT_PW')


if baseuri:
    api.baseURI = baseuri
api.login(codit_email, codit_pw)


def test_list_projects():
    _ = api.listProjects()

def test_list_inheritable_projects():
    _ = api.listInheritableProjects()

@pytest.mark.parametrize('async', [False, True])
def test_workflow(async):
    codebook = [
        {
            'id': 1,
            'label': 'Code 1',
            'category': 'CATEGORY 1'
        }, {
            'id': 20,
            'label': 'Code 2',
            'category': 'CATEGORY 2'
        }
    ]
    questions = [{'name': 'Question 1', 'codebook': codebook}]
    rows_init = [
        {
            "answers": [{"text":"Answer-text 1", "question": "Question 1"}],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
            # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
        },
        {
            "answers": [{"text":"Answer-text 2", "question": "Question 1"}],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        }
    ]
    num_projects_before = len(api.listProjects())
    new_project = api.createProject(
        "My new project",
        "de",
        auxiliary_column_names=['ID', 'some other column'],
        translate=True,
        questions=questions,
        rows=rows_init,
        async=async
    )
    time.sleep(10)
    num_projects_after = len(api.listProjects())
    assert num_projects_after == num_projects_before + 1
    assert len(new_project['questions']) == 1
    question_id = new_project['questions'][0]['id']
    additional_rows = [
        {
            "answers": [{"text":"Answer-text 1", "question": question_id}],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
            # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
        },
        {
            "answers": [{"text":"Answer-text 2", "question": question_id}],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        }
    ]
    new_answers = api.addRowsToProject(new_project['id'], additional_rows, async=async)

    time.sleep(10)
    answers = api.listAnswers(question_id, no_group=True)

    assert 4 == len(answers)

    _ = api.requestPredictions(question_id)

    time.sleep(250)

    predictions = api.getPredictions(question_id)

    _ = api.deleteProject(new_project['id'])

    assert num_projects_before == len(api.listProjects())
