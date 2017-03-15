import os
import unittest
import inflection

from email.utils import parsedate
from datetime import datetime
from pyramid import testing
from six import text_type

from pyramid.config import Configurator

from .base import DATA_DIR
from .resource import BOOKS


class ResourceFunctionalTests(unittest.TestCase):

    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
            'pyramlson.debug': 'true',
            'pyramlson.arguments_transformation_callback': inflection.underscore,
            'pyramlson.convert_parameters': 'false'
        }
        self.config = testing.setUp(settings=settings)
        self.config.include('pyramlson')
        self.config.scan('.resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def tearDown(self):
        testing.tearDown()

    def test_get_list_json(self):
        r = self.testapp.get('/api/v1/books', status=200)
        assert r.json_body == list(BOOKS.values())

    def test_get_one(self):
        app = self.testapp
        r = app.get('/api/v1/books/123', status=200)
        assert r.json_body == BOOKS[123]
        r = app.get('/api/v1/books/456', status=200)
        assert r.json_body == BOOKS[456]

    def test_get_notfound(self):
        app = self.testapp
        r = app.get('/api/v1/books/111', status=404)
        assert r.json_body['success'] == False
        assert r.json_body['message'] == "Book with id 111 could not be found."

        book_id = 10
        fake_book = {'id': book_id, 'title': 'Foo', 'author': 'Blah'}
        r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=404)
        assert r.json_body['success'] == False
        assert r.json_body['message'] == "Book with id {} could not be found.".format(book_id)

    def test_get_general_error(self):
        app = self.testapp
        r = app.get('/api/v1/books/zzz', status=400)
        assert r.json_body['success'] == False
        assert "Malformed parameter 'bookId'" in r.json_body['message']

    def test_json_validation_error(self):
        app = self.testapp
        r = app.put('/api/v1/books/111', status=400)
        assert r.json_body['message'] == "Empty body!"
        assert r.json_body['success'] == False

        r = app.request('/api/v1/books/111',
            method='PUT',
            body=b'{',
            status=400,
            content_type='application/json')
        assert r.json_body['success'] == False
        assert str(r.json_body['message']).startswith("Invalid JSON body:")

        book_id = 10
        fake_book = {'author': 'Blah'}
        r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=400)
        assert r.json_body['success'] == False
        assert 'Failed validating' in r.json_body['message']

    def test_not_accepted_body_mime_type(self):
        app = self.testapp
        r = app.request('/api/v1/books/123',
            method='PUT',
            body=b'hi there',
            status=400,
            content_type='text/plain')
        assert r.json_body['success'] == False
        assert "Invalid JSON body:" in r.json_body['message']

    def test_succesful_json_put(self):
        app = self.testapp
        book_id = 123
        fake_book = {'id': book_id, 'title': 'Foo', 'author': 'Blah'}
        r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=200)
        assert r.json_body['success'] == True


    def test_default_options(self):
        app = self.testapp
        r = app.options('/api/v1/books', status=204)
        header = r.headers['Access-Control-Allow-Methods'].split(', ')
        assert 'POST' in header
        assert 'GET' in header
        assert 'OPTIONS' in header

    def test_required_uriparams(self):
        app = self.testapp
        tt = 'a'
        r = app.get('/api/v1/books/some/other/things', params=dict(thingType=tt), status=200)
        # note the renamed argument
        assert r.json_body['thing_type'] == tt

    def test_missing_required_uriparams(self):
        app = self.testapp
        tt = 'a'
        r = app.get('/api/v1/books/some/other/things', params=dict(foo='bar'), status=400)
        assert r.json_body['message'] == 'thingType (string) is required'

class NoMatchingResourceMethodTests(unittest.TestCase):

    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
        }
        self.config = testing.setUp(settings=settings)

    def test_valueerror(self):
        self.config.include('pyramlson')
        self.assertRaises(ValueError, self.config.scan, '.bad_resource')


def datetime_adapter(obj, request):
    return obj.isoformat()


class ParamsConverterTests(unittest.TestCase):

    def setUp(self):
        from pyramid.renderers import JSON
        json_renderer = JSON()
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
            'pyramlson.debug': 'true',
            'pyramlson.arguments_transformation_callback': inflection.underscore,
            'pyramlson.convert_parameters': 'true'
        }
        self.config = testing.setUp(settings=settings)
        self.config.include('pyramlson')
        json_renderer.add_adapter(datetime, datetime_adapter)
        self.config.add_renderer('json', json_renderer)
        self.config.scan('.resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def test_param_type_conversion(self):
        date_str = 'Sun, 06 Nov 1994 08:49:37 GMT'
        date = datetime(*parsedate(date_str)[:6])
        params = {
            'maxString': 'zzz',
            'minString': 'tt',
            'choiceString': 'bar',
            'patternString': 'ABCD54321',
            'someNumber': '7',
            'minMaxNumber': '0.8',
            'minMaxInteger': '20',
            'someBool': 'true',
            'someDate': date_str
        }
        r = self.testapp.get('/api/v1/parametrized', params=params)
        b = r.json_body
        assert type(b['max_string']) is text_type
        assert type(b['min_string']) is text_type
        assert type(b['choice_string']) is text_type
        assert type(b['pattern_string']) is text_type
        assert type(b['some_number']) is int
        assert type(b['min_max_number']) is float
        assert type(b['min_max_integer']) is int
        assert type(b['some_bool']) is bool
        assert b['some_date'] == datetime_adapter(date, None)

    def test_string_param_validation(self):
        params = {
            'maxString': 'z' * 20,
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert "Malformed parameter 'maxString'" in r.json_body['message']
        assert "expected maximum length is 10, got 20" in r.json_body['message']

        params = {
            'minString': 'z'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
                "Malformed parameter 'minString', expected minimum length is 2, got 1"

        params = {
            'choiceString': 'biteme'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
                "Malformed parameter 'choiceString', expected one of foo, bar, blah, got 'biteme'"

        params = {
            'patternString': 'biteme'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Malformed parameter 'patternString', expected pattern ^[A-Z]{4}[0-9]*$, got 'biteme'"

    def test_number_param_validation(self):
        params = {
            'someNumber': 'Rasdf'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Malformed parameter 'someNumber', expected a syntactically valid number, got 'Rasdf'"

        params = {
            'minMaxNumber': '-400.456'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Parameter 'minMaxNumber' is too small, expected at least -10, got -400.456"

        params = {
            'minMaxNumber': '800.800'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Parameter 'minMaxNumber' is too large, expected at most 100.55, got 800.8"

    def test_integer_param_validation(self):
        params = {
            'minMaxInteger': '4.08'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Malformed parameter 'minMaxInteger', expected a syntactically valid integer, got '4.08'"

        params = {
            'minMaxInteger': '0'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Parameter 'minMaxInteger' is too small, expected at least 7, got 0"

        params = {
            'minMaxInteger': '100'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert r.json_body['message'] == \
            "Parameter 'minMaxInteger' is too large, expected at most 42, got 100"

    def test_bool_param_validation(self):
        params = {
            'someBool': 'yes'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert "Malformed boolean parameter 'someBool'" in r.json_body['message']
        assert "expected 'true' or 'false', got 'yes'" in r.json_body['message']

    def test_date_param_validation(self):
        params = {
            'someDate': '2016-1-11'
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert "Malformed parameter 'someDate'" in r.json_body['message']
        assert "expected RFC 2616 formatted date, got 2016-1-11" in r.json_body['message']

        date_str = 'Sun, 06 Nov 1000 53:78:37'
        params = {
            'someDate': date_str
        }
        r = self.testapp.get('/api/v1/parametrized', params=params, status=400)
        assert "Malformed parameter 'someDate':" in r.json_body['message']
        assert "hour must be in 0..23" in r.json_body['message']

    def test_missing_default_in_raml(self):
        r = self.testapp.get('/api/v1/parametrized', status=200)
        assert "defined in method!" == r.json_body['missing_default']
