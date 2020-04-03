import os
import argparse
from PyInquirer import style_from_dict, Token, prompt
from PyInquirer import Validator, ValidationError
import getpass
import time

from src.caplena_api_demo import CaplenaAPI

BATCH_SIZE = 2000

parser = argparse.ArgumentParser(description='Script to change inheritance on a question \n')

# parse credentials from environment variables
caplena_api_key = os.environ.get('CAPLENA_API_KEY')

api = CaplenaAPI('en', caplena_api_key)


class QuestionExistsValidator(Validator):
    def validate(self, document):
        try:
            question_id = int(document.text)
        except TypeError as e:
            raise TypeError('Project ID must be an integer')
        _ = api.getQuestion(question_id)


if __name__ == "__main__":

    prompt_question = [
        {
            'type': 'input',
            'name': 'question_id',
            'message': 'Please enter the question for which to modify inheritance',
            'validate': QuestionExistsValidator
        },
    ]
    prompt_answers = prompt(prompt_question)
    question = api.getQuestion(prompt_answers['question_id'])
    linked_question = api.getQuestion(question.inherits_from)
    print(
        'Question {}: {} currently inherits from ("learns from") question {}: {}'.format(
            question.id, question.name, linked_question.id, linked_question.name
        )
    )
    # prepare data for copy
    prompt_question = [
        {
            'type': 'input',
            'name': 'new_inherits_from',
            'message': 'Please enter the question id you would like to link to ("learn from")',
            'validate': QuestionExistsValidator
        },
    ]
    prompt_answers = prompt(prompt_question)
    # create project
    question.inherits_from = int(prompt_answers['new_inherits_from'])
    mod_question = api.updateQuestion(question, request_training=True)
    api.requestPredictions(mod_question.id)

    print(
        'Successfully linked question {} to {} and requested training'.format(
            mod_question.id, mod_question.inherits_from
        )
    )
