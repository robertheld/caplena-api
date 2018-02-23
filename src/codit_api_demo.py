# -*- coding: utf-8 -*-
"""Demo script illustrating how to do basic operations on the Codit API

Example
-------
Steps to run:

1. Make sure you have a compatible (version >= 2.7) python environment
    $ python --version
2. Make sure you have installed the requests library (if not, install using `pip install requests`)
    $ pip install requests
3. Adapt the `CODIT_EMAIL` and `CODIT_PASSWORD` variables at the bottom of this script
4. Call the script
    $ python codit_api_demo.py

Notes
-----
This script is not intended to be shared with third parties.
Every receiving party agrees to use it solely for own purposes
and purposes that are intended by the original author (Caplena GmbH).

Copyright 2018 Caplena GmbH, Zurich.
"""

import requests


class CoditAPI(object):
    """Class enabling interaction with (parts of) the Codit.co API

    Example
    -------
    To call an API instantiate a CoditAPI object and then call its methods
        >>> api = CoditAPI('de')
        >>> api.login('my_username', 'my_password')
        True
        >>> api.listSurveys()
        [{"name": "survey 1", "codebook": [{...}]}, {"name": "Survey 2", ...}, ...]

    """
    _valid_languages = ['en', 'de']

    def __init__(self, language):
        """
        API Class Initializer.

        Sets some basic attributes of the instance (e.g. base URL and content language)
        and initializes a session object which will be used for all subsequent API calls,
        as authentication is based on session cookies.

        Parameters
        ----------
        language : str
            Content-Language for API calls (mainly relevant for error messages), either "de" or "en"

        Returns
        -------

        """
        super(CoditAPI, self).__init__()
        self.csrftoken = None
        self.authenticated = False
        self.baseURI = "https://api.codit.co/api"

        if language not in self._valid_languages:
            raise ValueError("Invalid language '{}', accepted values are {{{}}}".format(
                language, ",".join(self._valid_languages)))
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
            "X-CSRFTOKEN": self.csrftoken
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

        Returns
        -------

        """
        raise Exception("ERROR (status code {}): {}".format(response.status_code, response.text))
        return False

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
        data : dict
            Data to be sent to API as json. Dictionary of key/value pairs (not-serialized!)
            Can contain all kind of JSON-serializeable objects, i.e. (in python terms)
            string|float|int|long|list|dictionary|boolean|none
        publicmethod : bool
            Flag indicating if authentication / csrftoken is required for this API method.
            Only set to True for public endpoints, such as `login`
            (optional)

        Returns
        -------
        response : requests::response obj
            Response object containing information about the servers response

        """

        if not publicmethod and (self.csrftoken is None or not self.authenticated):
            raise Exception(
                "CSRF-Token / authentication not set. Call login(..) before invoking other API calls")
        return getattr(self.sess, method)(
            "{}{}".format(self.baseURI, apiURI), json=data, headers=self._getHeaders())

    def login(self, email, password):
        """
        API method to authenticate user.

        Validates email & password credentials with server.
        If the login is successful, all subsequent API calls will be made as this user.
        The email & password are not saved, for authentication the session cookie is relevant.
        We also use this function to retrieve the CSRF-Token from the cookies.
        (see `_getHeaders()` for more information on the CSRF-Token)

        Parameters
        ----------
        email : str
            Email of the user to be logged in
        password : str
            Password of the user to be logged in
        data : dict
            Data to be sent to API as json. Dictionary of key/value pairs (not-serialized!)
            Can contain all kind of JSON-serializeable objects, i.e. (in python terms)
            `str|float|int|long|list|dictionary|bool|None`

        Returns
        -------
        success : bool
            True if login was successful, `False` otherwise

        """
        r = self._makeRequest(
            'post', '/auth/login/', {"email": email,
                                     "password": password}, publicmethod=True)

        if (r.status_code != 200):
            return self._handleBadResponse(r)
        else:
            self.csrftoken = self.sess.cookies['csrftoken']
            self.authenticated = True
            return True

    def listSurveys(self):
        """
        API method to list all surveys that belong to this user.

        List all surveys of the user.

        *Note:* The returned surveys only contain global meta information to the surveys and not the response texts.
        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------

        Returns
        -------
        surveys : list of survey objects
            A list of all surveys belonging to the user if the call was successful, `False` otherwise

        """
        r = self._makeRequest('get', '/surveys/')

        if (r.status_code != 200):
            return self._handleBadResponse(r)
        else:
            return r.json()

    def createSurvey(self,
                     name,
                     codebook,
                     language,
                     auxiliary_column_names=[],
                     description='',
                     inherits_from=None,
                     translate=False):
        """
        API method to create a new survey.

        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------
        name : str, required
            Name of the new survey
        codebook : list, required
            List of codes (dictionaries), each containing the keys `id`, `label` and `category`
            Can also be an empty list.
        language : str, required
            Language of the survey, valid choices are {en|de}
            Has nothing to do with the language the API is set to (the attribute `language`.)
        auxiliary_column_names : list, optional
            List of strings, naming additional columns that will be sent with each answer.
            Can also be an empty list.
            The number of elements in this list must match the number of elements
            in the `auxiliary_columns` field when adding answers later on.
        description : str, optional
            String describing this survey
        inherits_from : int, optional
            ID of another survey of this user, that the model should be based on.
            The codebook of that survey should be *identical* or *almost* identical
            in order for the AI to deliver good results.
        translate : bool, optional
            Flat indicating whether to translate this survey (where other language than `language` detected)
            using the Google API.

        Returns
        -------
        survey : survey object
            A dictionary containing all attributes of the newly created survey if the call was successful
            `False` otherwise

        """

        if language not in self._valid_languages:
            raise ValueError("Invalid language '{}', accepted values are {{{}}}".format(
                language, ",".join(self._valid_languages)))

        data = {
            "name": name,
            "codebook": codebook,
            "surveytype": 'FO',
            "language": language,
            "auxiliary_column_names": auxiliary_column_names,
            "description": description,
            "inherits_from": inherits_from,
            "translated": 1 if translate else 0
        }

        r = self._makeRequest('post', '/surveys/', data)

        if (r.status_code != 201):
            return self._handleBadResponse(r)
        else:
            return r.json()

    def addAnswersToSurvey(self, survey_id, answers):
        """
        API method to add answers to a previously created survey.

        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------
        survey_id : int
            ID of the survey to add the answers to
        answers : list(:class:`.Answer`)
            List of objects of type Answer

        Returns
        -------
        answers : list of answer objects
            A list of dictionaries containing attributes of the newly created answers if the call was successful
            `False` otherwise
            *Note:* When bulk creating multiple answers, no id is return for these elements

        """
        r = self._makeRequest('post', '/surveys/{}/answers'.format(survey_id), answers)

        if (r.status_code != 201):
            return self._handleBadResponse(r)
        else:
            return r.json()

    def listAnswers(self, survey_id):
        """
        API method to list all answers of a specific survey.

        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------
        survey_id : int
            ID of the survey of which to return the answers

        Returns
        -------
        answers : list(:class:`.Answer`)
            A list of all answers belonging to the survey if the call was successful, `False` otherwise

        """
        r = self._makeRequest('get', '/surveys/{}/answers'.format(survey_id))

        if (r.status_code != 200):
            return self._handleBadResponse(r)
        else:
            return r.json()

    def requestPredictions(self, survey_id):
        """
        API method to request the AI-assistant to train itself based on coded answers of specified survey. Only works
        if at least 6 answers have been coded.

        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------
        survey_id : int
            ID of the survey of which to request AI to make predictions

        Returns
        -------
        success : boolean
            True if request successful, False otherwise

        """
        r = self._makeRequest('post', '/surveys/{}/request-training'.format(survey_id))

        if (r.status_code != 200):
            return self._handleBadResponse(r)
        else:
            return r.json()

    def getPredictions(self, survey_id):
        """
        API method to get AI-coded codes and respective answers. Requires previous call to
        :func:`~codit_api_demo.CoditAPI.requestPredictions`.

        *Note:* For this method to work, a successfull call to :func:`~codit_api_demo.CoditAPI.login` is
        required beforehand

        Parameters
        ----------
        survey_id : int
            ID of the survey of which to return the code predictions made by AI

        Returns
        -------
        result : dict
            None if no predictions are available (response code 204)
            Otherwise contains keys `answers` (with itself has keys `id` and `codes`) which are the predictions, n_trainings (counter), training_completed (iso timestamp), model (meta information on model performance)

        """
        r = self._makeRequest('get', '/surveys/{}/codes-predicted'.format(survey_id))

        if (r.status_code == 204):
            # No content is available, i.e. no predictions are ready for this answer
            return None
        elif (r.status_code == 200):
            return r.json()
        else:
            return self._handleBadResponse(r)


class Answer(dict):
    """
    Answer object, purely for reference

    Attributes
    ----------
    text : str, required
        Text of the answer.
    auxiliary_columns: list(str), optional
        Only required if survey has `len(auxiliary_column_names)>0`
    reviewed : bool, optional
        Answers having the "reviewed" are assumed to have all codes correct
        and will be used to train the AI.
    codes : list, optional
        List of integers (code IDs). Assigning codes to an answer.
        Will be used to train the AI.

    """


if __name__ == '__main__':
    """ The main function invoked when calling this script directly"""

    ###########################################################
    # WARNING
    # This is only for demo purposes
    # Never hard-code credentials in a production environment
    # Rather pass them via environment variables or other means
    # >>> password = os.environ["MY_CODIT_PASSWORD"]
    ###########################################################

    CODIT_EMAIL = 'name@domain.com'
    CODIT_PASSWORD = '**************'

    # Instantiate new instance of CoditAPI class
    api = CoditAPI('en')

    # Call the login method before doing anything else
    # This sets all session parameters required for further calls
    login_success = api.login(CODIT_EMAIL, CODIT_PASSWORD)

    if login_success:
        print("Login Successful!")

    ###########################################################
    # LIST SURVEYS: Get all existing surveys of this user
    ###########################################################
    existing_surveys = api.listSurveys()

    # Count how many surveys we have
    print("There are {} existing surveys".format(len(existing_surveys)))

    ###########################################################
    # CREATE SURVEY: Create new survey and get its ID
    ###########################################################
    codebook = [{
        'id': 1,
        'label': 'Code 1',
        'category': 'CATEGORY 1'
    }, {
        'id': 20,
        'label': 'Code 2',
        'category': 'CATEGORY 2'
    }]

    new_survey = api.createSurvey(
        "My new survey",
        codebook,
        "de",
        auxiliary_column_names=['ID', 'some other column'],
        description="Some description of survey",
        translate=True)
    if new_survey is not False:
        print("Created new survey with id {}".format(new_survey['id']))

    ###########################################################
    # CREATE ANSWERS: Add answers to existing survey
    ###########################################################
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
    if new_answers is not False:
        print("Added {} new answers to survey {}".format(len(new_answers), new_survey['id']))

    ###########################################################
    # LIST ANSWERS: Get all answers of a specific survey
    ###########################################################
    answers = api.listAnswers(new_survey['id'])

    print("The first answer ('{}') has been assigned the codes: {}".format(answers[0]['text'],
                                                                           answers[0]['codes']))

    ###########################################################
    # REQUEST PREDICTIONS: Instruct backend to make code predictions for survey
    ###########################################################

    if api.requestPredictions(new_survey['id']):
        print("Training request made, results will soon be available")
    else:
        print("An error occurred when requesting training")

    ###########################################################
    # GET PREDICTIONS: Return the predictions made by the model
    ###########################################################

    # In a practical setting, there needs to be some time in between requesting the predictions
    # and getting them back. In most cases, they will be ready within ~20s, but to be sure a value
    # of around 250s is recommended
    # time.sleep(250)

    predictions = api.getPredictions(new_survey['id'])

    if predictions is None:
        print("No predictions are ready for this survey")
    elif 'answers' in predictions and len(predictions['answers']) > 0:
        print("For answer {} the codes {} were predicted".format(predictions['answers'][0]['id'],
                                                                 predictions['answers'][0]['codes']))
