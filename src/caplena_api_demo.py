# -*- coding: utf-8 -*-
"""Demo script illustrating how to do basic operations on the Caplena API

Example
-------
Steps to run:

1. Make sure you have a compatible (version >= 2.7) python environment
    $ python --version
2. Make sure you have installed the requests library (if not, install using `pip install requests`)
    $ pip install requests
3. Set the `CAPLENA_API_KEY` variable at the bottom of this script
4. Call the script
    $ python caplena_api_demo.py

Notes
-----
This script is not intended to be shared with third parties.
Every receiving party agrees to use it solely for own purposes
and purposes that are intended by the original author (Caplena GmbH).

Copyright 2018 Caplena GmbH, Zurich.
"""
import requests
import time
import json
import six

if six.PY2:
    from urllib import urlencode
else:
    from urllib.parse import urlencode

from src.utils import CaplenaObj, ComplexEncoder


class CaplenaAPI(object):
    """Class enabling interaction with (parts of) the Caplena.co API

    Example
    -------
    To call an API instantiate a CaplenaAPI object and then call its methods
        >>> api = CaplenaAPI('de', '$(API_KEY)')
        >>> api.listProjects()
        [{"name": "project 1",
         "questions": [{"name": "question A"}, ...]},
         "rows": [{"answers": [{...}, ...], "auxiliary_columns": [...]}]
        ]

    """
    valid_languages = ['en', 'de']

    def __init__(self, language, api_key):
        """
        API Class Initializer.

        Sets some basic attributes of the instance (e.g. base URL and content language)
        and initializes a session object which will be used for all subsequent API calls,
        as authentication is based on session cookies.

        Parameters
        ----------
        language : str
            Content-Language for API calls (mainly relevant for error messages), either "de" or "en"
        api_key: str
            API key to authenticate to the Caplena API, if you don't have a key, please contact support@caplena.com

        Returns
        -------

        """
        super(CaplenaAPI, self).__init__()
        self.api_key = api_key
        self.authenticated = False
        self.baseURI = "https://api.caplena.com/api"

        if language not in self.valid_languages:
            raise ValueError(
                "Invalid language '{}', accepted values are {{{}}}".format(
                    language, ",".join(self.valid_languages)
                )
            )
        else:
            self.language = language

        self.sess = requests.Session()

    def _getHeaders(self):
        """
        Internal function to generate global header for all API calls

        The following headers are returned:
        * `Content-Type`:       We always use json format for the data we send
        * `Accept`:             We always expect json back from the server
        * `Accept-Language`:    The language for API messages (and in some cases content), supported: {en|de}
        * `X-CSRFTOKEN`:        Cross-site-request-forgery token (security). Token which set by the server to
                                a cookie and  required to be sent as a header in all DB-modifying requests
                                (i.e. types POST, PATCH, DELETE, PUT)

        Parameters
        ----------

        Returns
        -------
        headers : dict
            Dictionary with keys being the header names and values the header values

        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": self.language,
            "Authorization": "apikey {}".format(self.api_key),
            "Referer": self.baseURI
        }
        return headers

    def _handleBadResponse(self, response):
        """
        Internal function to handle unsuccessful requests

        Currently a dummy function which just raises an error with the reponse text.
        Can be adjusted to do a more fine-grained error handling.

        Parameters
        ----------
        response : requests::response object
            The response object which failed

        -------

        """
        raise Exception("ERROR (status code {}): {}".format(response.status_code, response.text))

    def _makeRequest(self, method, apiURI, data=None, publicmethod=False):
        """
        Internal function to make the API call.

        Currently a very thin wrapper around `requests` library.
        Only does two things
        * Get and set headers by calling `_getHeaders()`
        * Concatenate the base URI and the api URI

        Parameters
        ----------
        method : str
            HTTP request method which should be called (i.e. GET / POST / ...)
            Needs to be a method of requests, otherwise function will fail
        apiURI : str
            The URI of the API method to call (only last part, the base URI including domain are class attributes)
        data : dict|list
            Data to be sent to API as json. Dictionary of key/value pairs (not-serialized!)
            Can contain all kind of JSON-serializeable objects, i.e. (in python terms)
            string|float|int|long|list|dictionary|bool|none
        publicmethod : bool
            Flag indicating if authentication is required for this API method.
            Only set to True for public endpoints
            (optional)

        Returns
        -------
        response : requests::response obj
            Response object containing information about the servers response

        """

        if not publicmethod and (self.api_key is None):
            raise Exception("API key not provided. Provide valid API key when instantiating CaplenaAPI")
        return getattr(self.sess, method)(
            "{}{}".format(self.baseURI, apiURI),
            data=json.dumps(data, cls=ComplexEncoder) if data else None,
            headers=self._getHeaders()
        )

    def listProjects(self):
        """
        API method to list all projects that belong to this user.

        List all projects of the user.

        *Note:* The returned projects contain global meta information of the projects *and* their questions, but not the response texts.

        Parameters
        ----------

        Returns
        -------
        projects : list(:class:`.Project`)
            A list of all projects belonging to the user

        """
        r = self._makeRequest('get', '/projects/')

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Project.from_json(data) for data in r.json()]

    def listInheritableProjects(self):
        """
        API method to list all projects of which inheritance is possible.

        List contains all projects belonging to user, as well as Caplena provided models.

        *Note:* The returned projects only contain basic meta information on the project and their questions, but not the response texts. To get more detailed information about a certain project call the `listprojects` method.

        Parameters
        ----------

        Returns
        -------
        projects : list(:class:`.Project`)
            A list of all projects that can be used for inheritance. This is the concatenation of all projects owned by the user and global Caplena models.

        """
        r = self._makeRequest('get', '/projects-inheritable/')

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Project.from_json(data) for data in r.json()]

    def listQuestions(self):
        """
        API method to list all questions that belong to this user.

        List all questions of the user.

        *Note:* The returned questions only contain global meta information of the questions and not the response texts.

        Parameters
        ----------

        Returns
        -------
        questions: list(:class:`.Question`)
            A list of all questions belonging to the user if the call was successful, `False` otherwise

        """
        r = self._makeRequest('get', '/questions/')

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Question.from_json(data) for data in r.json()]

    def getQuestion(self, question_id):
        """
        API method to get question info.

        Get question by ID.

        *Note:* The returned questions only contain meta information of the question and not the response texts.

        Parameters
        ----------

        Returns
        -------
        question : Question
            A question object

        """
        r = self._makeRequest('get', '/questions/{}'.format(question_id))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return Question.from_json(r.json())

    def getProject(self, project_id):
        """
        API method to get project info.

        Get project by ID.

        *Note:* The returned questions only contain meta information of the question and not the response texts.

        Parameters
        ----------

        Returns
        -------
        project : Project
            A project object

        """
        r = self._makeRequest('get', '/projects/{}'.format(project_id))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return Project.from_json(r.json())

    def createProject(
        self,
        name,
        language,
        translate=False,
        auxiliary_column_names=[],
        questions=[],
        rows=[],
        translation_engine='GT',
        upload_async=True,
        request_training=True
    ):
        """
        API method to create a new project

        *Note:*
        * When creating a new project you can also create questions and rows belonging to it.
        * Creating new questions is _only_ possible when creating a new project. Questions cannot be added to an
        existing project.
        * Rows can also be added to a project at a later time

        Parameters
        ----------
        name : str, required
            Name of the new project
        language : str, required
            Language of the project, valid choices are {en|de}
            Has nothing to do with the language the API is set to (the attribute `language`.)
        translate : bool, optional
            Flag indicating whether to translate this project (where other language than `language` detected)
            using the Google API.
        auxiliary_column_names : list, optional
            List of strings, naming additional columns that will be sent with each row.
            Can also be an empty list.
            The number of elements in this list must match the number of elements
            in the `auxiliary_columns` field when adding rows.
        questions : list(:class:`.Question`)
            List of questions to create
        rows : list(:class:`.Row`)
            List of objects of type Row
        async : bool
            If true, send async request, required if uploading more than 20 rows at once or if uploading answers
            with `reviewed=True`
        request_training : bool
            If true, automatically request training after uploading answers
        translation_engine : str
            Choice of translation engine, either 'GT' for Google Translate or 'DL' for DeepL
        Returns
        -------
        project : Project
            A new Project object

        """
        proj = Project(
            name=name,
            language=language,
            translate=translate,
            auxiliary_column_names=auxiliary_column_names,
            questions=questions,
            rows=rows,
            translation_engine=translation_engine
        )
        get_params = {'request_training': request_training}
        if upload_async:
            get_params.update({'async': upload_async})
        get_params = '?' + urlencode(get_params)
        r = self._makeRequest('post', '/projects/{}'.format(get_params), proj.to_dict())

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return Project.from_json(r.json())

    def addRowsToProject(self, project_id, rows, upload_async=True, request_training=True):
        """
        API method to add rows to a previously created project.


        Parameters
        ----------
        project_id : int
            ID of the project to add the rows to
        rows : list(:class:`.Row`)
            List of objects of type Row
        async : bool
            If true, send async request, required if uploading more than 20 rows at once or if uploading answers
            with `reviewed=True`
        request_training : bool
            If true, automatically request training after uploading answers

        Returns
        -------
        rows: list(:class:`.Row`)
            A list of the newly created rows

        """
        get_params = {'request_training': request_training}
        if upload_async:
            get_params.update({'async': upload_async})
        get_params = '?' + urlencode(get_params)
        r = self._makeRequest(
            'post', '/projects/{}/rows{}'.format(project_id, get_params), [row.to_dict() for row in rows]
        )

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Row.from_json(dat) for dat in r.json()]

    def listRows(self, project_id):
        """
        API method to list all rows of a specific project.


        Parameters
        ----------
        project_id : int
            ID of the project of which to return the rows

        Returns
        -------
        answers : list(:class:`.Row`)
            A list of all rows belonging to the question

        """
        r = self._makeRequest('get', '/projects/{}/rows'.format(project_id))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Row.from_json(dat) for dat in r.json()]

    def listAnswers(self, question_id, no_group=False):
        """
        API method to list all answers of a specific question.


        Parameters
        ----------
        question_id : int
            ID of the question of which to return the answers
        no_group : bool
            If true, no grouping will be applied to answers list,
            overriding the `group_identical` property of the question

        Returns
        -------
        answers : list(:class:`.Answer`)
            A list of all answers belonging to the question

        """
        get_params = '?no_group' if no_group else ''
        r = self._makeRequest('get', '/questions/{}/answers{}'.format(question_id, get_params))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Answer.from_json(dat) for dat in r.json()]

    def requestPredictions(self, question_id, **kwargs):
        """
        API method to request the AI-assistant to train itself based on coded answers of specified question. Only works
        if at least 6 answers have been coded.


        Parameters
        ----------
        question_id : int
            ID of the question of which to request AI to make predictions

        Returns
        -------
        success : bool
            True if request successful, False otherwise

        """
        request_url = '/questions/{}/request-training'.format(question_id)
        if kwargs:
            parameters = '?' + urlencode(kwargs)
            request_url += parameters
        r = self._makeRequest('post', request_url)

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return True

    def getPredictions(self, question_id):
        """
        API method to get AI-coded codes and respective answers. Requires previous call to
        :func:`~caplena_api_demo.CaplenaAPI.requestPredictions`.


        Parameters
        ----------
        question_id : int
            ID of the question of which to return the code predictions made by AI

        Returns
        -------
        result : Predictions|None
            None if no predictions are available (response code 204)
            Otherwise contains keys `answers` (with itself has keys `id` and `codes`) which are the predictions, model (meta information on model performance)

        """
        r = self._makeRequest('get', '/questions/{}/codes-predicted'.format(question_id))

        if (r.status_code == 204):
            # No content is available, i.e. no predictions are ready for this answer
            return None
        elif (r.status_code == 200):
            return Predictions.from_json(r.json())
        else:
            return self._handleBadResponse(r)

    def deleteQuestion(self, question_id):
        """
        API method to delete question and its answers.


        Parameters
        ----------
        question_id : int
            ID of the question to delete

        Returns
        -------
        success : bool
            True if request successful, False otherwise

        """
        r = self._makeRequest('delete', '/questions/{}'.format(question_id))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return True

    def deleteProject(self, project_id):
        """
        API method to delete projects, its questions and corresponding answers.


        Parameters
        ----------
        project_id : int
            ID of the project to delete

        Returns
        -------
        success : bool
            True if request successful, False otherwise

        """
        r = self._makeRequest('delete', '/projects/{}'.format(project_id))

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return True

    def updateQuestion(self, question, request_training=False):
        """
        API method to update question


        Parameters
        ----------
        question: question
            modified question instance

        Returns
        -------
        question: Question
            newly updated question instance

        """
        get_params = {'request_training': request_training}
        get_params = '?' + urlencode(get_params)
        r = self._makeRequest('patch', '/questions/{}{}'.format(question.id, get_params), question.to_dict())

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return Question.from_json(r.json())

    def updateAnswers(self, answers, question, request_training=False):
        """
        API method to update question


        Parameters
        ----------
        question: question
            modified question instance

        Returns
        -------
        question: Question
            newly updated question instance

        """
        get_params = {'request_training': request_training}
        get_params = '?' + urlencode(get_params)
        r = self._makeRequest(
            'patch', '/questions/{}/answers{}'.format(question.id, get_params),
            [ans.to_dict() for ans in answers]
        )

        if (not r.ok):
            return self._handleBadResponse(r)
        else:
            return [Answer.from_json(el) for el in r.json()]


class Code(CaplenaObj):
    """
    Code object

    Attributes
    ----------
    id: int, required
        Code ID
    label: str, required
        Code name
    category: str, required
        Code category
    """
    def __init__(self, id, label, category, **kwargs):
        """
        """
        self.id = id
        self.label = label
        self.category = category
        super(Code, self).__init__(**kwargs)

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class Question(CaplenaObj):
    """
    Question object

    Attributes
    ----------
    name : str, required
        Name of the question.
    description : str, optional
        String describing this question
    group_identical : bool, optional
        Flag indicating whether to group identical answers in coding view and when listing answers.
        Default=true
    group_identical_exclude : str, optional
        All answer texts matching this regular expression won't be grouped. Default=''
    smart_sort: bool, optional
        If the smart sorting feature should be enabled. Default=true
    codebook : list(:class:`.Code`), optional
        List of codes (dictionaries), each containing the keys `id`, `label` and `category`
        Can also be an empty list.
    inherits_from : int, optional
        ID of another question of this user, that the model should be based on.
        The codebook of that question should be *identical* or *almost* identical
        in order for the AI to deliver good results.

    """
    def __init__(
        self,
        name,
        description='',
        codebook=[],
        group_identical=True,
        group_identical_exclude='',
        smart_sort=False,
        inherits_from=None,
        id=None,
        question_category='NO',
        **kwargs
    ):
        self.name = name
        self.description = description
        self.group_identical = group_identical
        self.group_identical_exclude = group_identical_exclude
        self.smart_sort = smart_sort
        self.codebook = codebook
        self.inherits_from = inherits_from
        self.id = id
        self.question_category = question_category
        super(Question, self).__init__(**kwargs)

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class Answer(CaplenaObj):
    """
    Answer object

    Attributes
    ----------
    text : str, required
        Text of the answer.
    question : str, required
        The name of the question this answer belongs to
    reviewed : bool, optional
        Answers having the "reviewed" are assumed to have all codes correct
        and will be used to train the AI.
    codes : list(int), optional
        List of integers (code IDs). Assigning codes to an answer.
        Will be used to train the AI.
    source_language : str, optional
        ISO Code (2 characters, e.g. 'de' or 'en') specifying in which language the text is written.
        Relevant for translation, taking precedance over automatic language detection

    """
    def __init__(self, text, question, source_language='', reviewed=False, codes=[], id=None, **kwargs):
        self.id = id
        self.text = text
        self.question = question
        self.reviewed = reviewed
        self.codes = codes
        self.source_language = source_language
        super(Answer, self).__init__(**kwargs)

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class Row(CaplenaObj):
    """
    Row object

    Attributes
    ----------
    auxiliary_columns : list(str), required
        Needs to have the same number of elemenst as the `auxiliary_column_names` field of the project
        it belongs to
    answers : list(:class:`.Answer`), required
        A list of answers, whereby exactly one answer needs to be provided for every question of the project
        it belongs to
    """
    def __init__(self, auxiliary_columns, answers, **kwargs):
        self.auxiliary_columns = auxiliary_columns
        self.answers = answers
        super(Row, self).__init__(**kwargs)

    @classmethod
    def from_json(cls, json_data):
        ans = json_data.pop('answers')
        answers = list(map(Answer.from_json, ans))
        row = Row(answers=answers, **json_data)
        json_data['answers'] = ans
        return row


class Project(CaplenaObj):
    """
    Project object

    Attributes
    ----------
    name : str, required
        Name of the project.
    language: str, required
        Language of question, must be iso tag
    questions: list(:class:`.Questions`), required
        Questions belonging to the project
    auxiliary_column_names: list(str), optional
        Names of the auxiliary columns
    translation_engine: str, optional
        Which translation engine to use, can be either `google` or `deepl
    translate: bool, optional
        If true translate answers using translation_engine
    inherits_from : int, optional
        ID of another question of this user, that the model should be based on.
        The codebook of that question should be *identical* or *almost* identical
        in order for the AI to deliver good results.

    """
    def __init__(
        self,
        name,
        language,
        questions,
        rows=[],
        auxiliary_column_names=[],
        translation_engine='google',
        translate=False,
        translated=0,
        id=None,
        **kwargs
    ):
        self.name = name
        self.language = language
        self.auxiliary_column_names = auxiliary_column_names
        if translated:
            self.translate = True if translated else False
        else:
            self.translate = translate
        self.questions = questions
        self.rows = rows
        self.translation_engine = translation_engine
        self.id = id
        super(Project, self).__init__(**kwargs)

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "auxiliary_column_names": self.auxiliary_column_names,
            "translated": 1 if self.translate else 0,
            "translation_engine": self.translation_engine,
            "questions": self.questions,
            "rows": self.rows
        }
        return data

    @classmethod
    def from_json(cls, json_data):
        questions = list(map(Question.from_json, json_data.pop('questions')))
        if 'rows' in json_data.keys():
            row_data = json_data.pop('rows')
            rows = list(map(Row.from_json, row_data))
            proj = Project(rows=rows, questions=questions, **json_data)
            json_data['rows'] = row_data
            return proj
        else:
            proj = Project(questions=questions, **json_data)
            return proj


class Predictions(CaplenaObj):
    """
    answers : list(:class:`.Answer`), required
        A list of answers, whereby exactly one answer needs to be provided for every question of the project
        it belongs to
    model : dict, required
        Meta information about the model
    """
    def __init__(self, answers, model, **kwargs):
        self.answers = answers
        self.model = model
        super(Predictions, self).__init__(**kwargs)

    @classmethod
    def from_json(cls, json_data):
        return Predictions(**json_data)


if __name__ == '__main__':
    """ The main function invoked when calling this script directly"""

    ###########################################################
    # WARNING
    # This is only for demo purposes
    # Never hard-code credentials in a production environment
    # Rather pass them via environment variables or other means
    # >>> password = os.environ["MY_CAPLENA_PASSWORD"]
    ###########################################################

    CAPLENA_API_KEY = '*******'

    # Instantiate new instance of CaplenaAPI class
    api = CaplenaAPI('en', CAPLENA_API_KEY)

    ###########################################################
    # LIST PROJECTS: Get all existing projects of this user
    ###########################################################
    existing_projects = api.listProjects()

    # Count how many projects we have
    print("There are {} existing projects".format(len(existing_projects)))

    ###########################################################
    # CREATE PROJECT: Create new project with two questions and two rows (=> 4 answers)
    ###########################################################
    n_questions = 2
    new_questions = [
        Question(
            name='My new question {}'.format(question_number),
            description='Some description of question {}'.format(question_number),
            codebook=[
                {
                    'id': 1,
                    'label': 'Code 1 of question {}'.format(question_number),
                    'category': 'CATEGORY 1'
                }, {
                    'id': 20,
                    'label': 'Code 2 of question {}'.format(question_number),
                    'category': 'CATEGORY 2'
                }
            ]
        ) for question_number in range(n_questions)
    ]

    new_rows = [
        Row(
            auxiliary_columns=['ID 1', 'Some other column value 1'],
            answers=[
                Answer(
                    text='Answer-text row 1 of question {}'.format(question_number),
                    question='My new question {}'.format(question_number)
                ) for question_number in range(n_questions)
            ]
        ),
        Row(
            auxiliary_columns=['ID 2', 'Some other column value 2'],
            answers=[
                Answer(
                    text='Answer-text row 2 of question {}'.format(question_number),
                    question='My new question {}'.format(question_number)
                ) for question_number in range(n_questions)
            ]
        ),
    ]

    new_project = api.createProject(
        "My new project",
        language="de",
        auxiliary_column_names=['ID', 'some other column'],
        translate=True,
        questions=new_questions,
        rows=new_rows,
        request_training=False
    )

    if new_project is not False:
        print("Created new project with id {}".format(new_project.id))

    question_id_1 = new_project.questions[0].id
    question_id_2 = new_project.questions[1].id

    ###########################################################
    # ADD ROWS: Add one more row to existing project

    # Note: When adding rows to an _existing_ project, the questions need to referenced by their ID
    # not their name
    further_rows = [
        Row(
            auxiliary_columns=['ID 3', 'Some other column value 3'],
            answers=[
                Answer(text='Answer-text row 3 of question {}'.format(question_number), question=question_id)
                for question_id, question_number in zip([question_id_1, question_id_2], range(n_questions))
            ]
        )
    ]

    further_rows_result = api.addRowsToProject(new_project.id, further_rows, request_training=False)
    if further_rows_result is not False:
        print("Added {} new row to project {}".format(len(further_rows), new_project.id))

    ###########################################################
    # LIST ROWS: Get all rows of a specific project
    ###########################################################
    rows = api.listRows(new_project.id)

    print("This is the first row: {}".format(rows[0]))

    ###########################################################
    # LIST ANSWERS: Get all answers of a specific question
    ###########################################################
    answers = api.listAnswers(question_id_2)

    print(
        "The first answer ('{}') of question {} has been assigned the codes: {}".format(
            answers[0].text, question_id_2, answers[0].codes
        )
    )

    ###########################################################
    # REQUEST PREDICTIONS: Instruct backend to make code predictions for question
    ###########################################################

    if api.requestPredictions(question_id_1):
        print("Training request made, results will soon be available")
    else:
        print("An error occurred when requesting training")

    ###########################################################
    # GET PREDICTIONS: Return the predictions made by the model
    ###########################################################

    # In a practical setting, there needs to be some time in between requesting the predictions
    # and getting them back. In most cases, they will be ready within ~200s, but to be sure a value
    # of around 600s is recommended
    time.sleep(600)

    predictions = api.getPredictions(question_id_1)
    if predictions is None:
        print("No predictions are ready for this question")
    elif 'answers' in predictions and len(predictions['answers']) > 0:
        print(
            "For answer {} the codes {} were predicted".format(
                predictions['answers'][0].id, predictions['answers'][0].codes
            )
        )
