import os
import unittest
import inflection

from pyramid import testing

from pyramid.config import Configurator

from .base import DATA_DIR
from .resource import BOOKS


class ResourceFunctionalTests(unittest.TestCase):

    def setUp(self):
        settings = {
            'pyramlson.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
            'pyramlson.debug': 'true',
            'pyramlson.arguments_transformation_callback': inflection.underscore
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
        assert r.json_body['message'] == "Malformed parameter 'bookId', expected integer, got 'zzz'"

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
