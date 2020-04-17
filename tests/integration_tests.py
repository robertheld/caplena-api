import os, time

import pytest

from src.caplena_api_demo import CaplenaAPI, Question, Row, Answer, Project, Code

caplena_api_key = os.environ.get('CAPLENA_API_KEY')
api = CaplenaAPI('en', caplena_api_key)

baseuri = os.environ.get('BASEURI')

if baseuri:
    api.baseURI = baseuri

if os.environ.get('REPORT_ERRORS', False):
    import sentry_sdk
    sentry_sdk.init(os.environ.get('SENTRY_ENDPOINT'))


def test_list_projects():
    _ = api.listProjects()


def test_list_inheritable_projects():
    _ = api.listInheritableProjects()


def test_update_question():
    codebook = [Code(id=1, label='test', category='A')]
    question_name = 'testq'
    question = Question(name=question_name, codebook=codebook)
    rows = [
        Row(auxiliary_columns=[], answers=[Answer(text='test', question=question_name, reviewed=False)]),
        Row(auxiliary_columns=[], answers=[Answer(text='test2', question=question_name, reviewed=False)])
    ]
    proj1 = api.createProject('testproject', 'en', rows=rows, questions=[question], upload_async=False)
    proj2 = api.createProject('testproject', 'en', rows=rows, questions=[question], upload_async=False)
    print(proj1.id)
    print(proj2.id)
    print(api.listProjects())
    q = proj2.questions[0]
    q.inherits_from = proj1.questions[0].id
    print(q)
    q_new = api.updateQuestion(q)
    assert q_new.inherits_from == proj1.questions[0].id


def test_sync_workflow():
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
    # make sure to have at least 15 answers reviewed to enble predictions
    rows_init = [
                    {
                        "answers":
                            [{
                                "text": "Answer-text 1",
                                "question": "Question 1"
                            }],
                        "auxiliary_columns": ["ID 1", "Some other column value 1"]
                        # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
                    },
                    {
                        "answers": [{
                            "text": "Answer-text 2",
                            "question": "Question 1"
                        }],
                        "auxiliary_columns": ["ID 1", "Some other column value 1"]
                    },
                    {
                        "answers": [{
                            "text": "Answer-text 3",
                            "question": "Question 1"
                        }],
                        "auxiliary_columns": ["ID 1", "Some other column value 1"]
                    }
    ]
    num_projects_before = len(api.listProjects())
    questions = [Question.from_json(q) for q in questions]
    rows_init = [Row.from_json(row_init) for row_init in rows_init]
    new_project = api.createProject(
        name="My new project",
        language="de",
        auxiliary_column_names=['ID', 'some other column'],
        translate=True,
        questions=questions,
        rows=rows_init,
        upload_async=False,
        request_training=True
    )
    assert isinstance(new_project, Project)

    num_projects_after = len(api.listProjects())
    assert num_projects_after == num_projects_before + 1
    assert len(new_project.questions) == 1
    question_id = new_project.questions[0].id
    n_not_reviewed = len([row for row in rows_init if not row.answers[0].reviewed])
    assert new_project.rows is not None
    assert len(new_project.rows) == len(rows_init)

    additional_rows = [
        {
            "answers": [{
                "text": "Answer-text 1 new data",
                "question": question_id,
                "reviewed": False
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
            # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
        },
        {
            "answers": [{
                "text": "Answer-text 2 new data",
                "question": question_id,
                "reviewed": False
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        }
    ]
    try:
        new_answers = api.addRowsToProject(
            new_project.id, [Row.from_json(r) for r in additional_rows],
            upload_async=False,
            request_training=True
        )
        answers = api.listAnswers(question_id, no_group=True)
        assert len(rows_init) + len(additional_rows) == len(answers)
    finally:
        _ = api.deleteProject(new_project.id)
        assert num_projects_before == len(api.listProjects())


def test_workflow_async():
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
    # make sure to have at least 15 answers reviewed to enble predictions
    rows_init = [
        {
            "answers":
            [{
                "text": "Answer-text 1",
                "question": "Question 1",
                "codes": [1, 20],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
            # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
        },
        {
            "answers": [{
                "text": "Answer-text 2",
                "question": "Question 1",
                "codes": [1],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers": [{
                "text": "Answer-text 3",
                "question": "Question 1",
                "codes": [20],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers": [{
                "text": "Answer-text 4",
                "question": "Question 1",
                "codes": [20],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers":
            [{
                "text": "Answer-text 5",
                "question": "Question 1",
                "codes": [1, 20],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers": [{
                "text": "Answer-text 6",
                "question": "Question 1",
                "codes": [1],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers":
            [{
                "text": "Answer-text 7",
                "question": "Question 1",
                "codes": [1, 20],
                "reviewed": True
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers": [{
                "text": "Answer-text 8",
                "question": "Question 1",
                "reviewed": False
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        },
        {
            "answers": [{
                "text": "Answer-text 9",
                "question": "Question 1",
                "reviewed": False
            }],
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
        }
    ]
    num_projects_before = len(api.listProjects())
    questions = [Question.from_json(q) for q in questions]
    rows_init = [Row.from_json(row_init) for row_init in rows_init]
    new_project = api.createProject(
        name="My new project",
        language="de",
        auxiliary_column_names=['ID', 'some other column'],
        translate=True,
        questions=questions,
        rows=rows_init,
        upload_async=True,
        request_training=True
    )
    assert isinstance(new_project, Project)
    try:
        # wait a bit since this is async upload
        time.sleep(10)
        num_projects_after = len(api.listProjects())
        assert num_projects_after == num_projects_before + 1
        assert len(new_project.questions) == 1
        created_rows = api.listRows(new_project.id)
        question_id = new_project.questions[0].id

        n_not_reviewed_init = len([row for row in rows_init if not row.answers[0].reviewed])
        n_not_reviewed_after_create = len([row for row in created_rows if not row.answers[0].reviewed])
        assert n_not_reviewed_after_create == n_not_reviewed_init

        additional_rows = [
            {
                "answers": [{
                    "text": "Answer-text 1 new data",
                    "question": question_id,
                    "reviewed": False
                }],
                "auxiliary_columns": ["ID 1", "Some other column value 1"]
                # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
            },
            {
                "answers": [{
                    "text": "Answer-text 2 new data",
                    "question": question_id,
                    "reviewed": False
                }],
                "auxiliary_columns": ["ID 1", "Some other column value 1"]
            }
        ]
        new_rows = api.addRowsToProject(
            new_project.id, [Row.from_json(r) for r in additional_rows],
            upload_async=True,
            request_training=False
        )
        print(new_rows)
        assert 1 == 0
        time.sleep(10)
        answers = api.listAnswers(question_id, no_group=True)
        assert len(rows_init) + len(additional_rows) == len(answers)

    finally:
        _ = api.deleteProject(new_project.id)
        assert num_projects_before == len(api.listProjects())
