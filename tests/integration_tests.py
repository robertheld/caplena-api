import os, time

from src.codit_api_demo import CoditAPI


api = CoditAPI('en')

baseuri = os.environ.get('BASEURI')
codit_email = os.environ.get('CODIT_EMAIL')
codit_pw = os.environ.get('CODIT_PW')


if baseuri:
    api.baseURI = baseuri
api.login(codit_email, codit_pw)


def test_list_surveys():
    _ = api.listSurveys()

def test_list_inheritable_surveys():
    _ = api.listInheritableSurveys()

def test_workflow():
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
    num_surveys_before = len(api.listSurveys())
    new_survey = api.createSurvey(
        "My new survey",
        codebook,
        "de",
        auxiliary_column_names=['ID', 'some other column'],
        description="Some description of survey",
        translate=True
    )
    num_surveys_after = len(api.listSurveys())
    assert num_surveys_after == num_surveys_before + 1
    answers = [
        {
            "text": "Answer-text 1",
            "auxiliary_columns": ["ID 1", "Some other column value 1"]
            # The values of the additional columns: Needs to be in same order as auxiliary_column_names of survey
        },
        {
            "text": "Answer-text 2",
            "auxiliary_columns": ["ID 2", "Some other column value 2"]
        }
    ]
    new_answers = api.addAnswersToSurvey(new_survey['id'], answers)

    answers = api.listAnswers(new_survey['id'])

    assert len(new_answers) == len(answers)

    _ = api.requestPredictions(new_survey['id'])

    time.sleep(250)

    predictions = api.getPredictions(new_survey['id'])

    _ = api.deleteSurvey(new_survey['id'])

    assert num_surveys_before == len(api.listSurveys())
