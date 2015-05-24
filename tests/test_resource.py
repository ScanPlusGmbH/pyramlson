import os
import unittest

from pyramid import testing

from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy

from .base import DATA_DIR
from .resource import BOOKS


class ResourceFunctionalTests(unittest.TestCase):

    def setUp(self):
        settings = {
            'pyramid_raml.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
        }
        self.config = testing.setUp(settings=settings)
        self.config.include('pyramid_raml')
        self.config.scan('.resource')
        from webtest import TestApp
        self.testapp = TestApp(self.config.make_wsgi_app())

    def tearDown(self):
        testing.tearDown()

    def test_get_list(self):
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
        r = app.get('/api/v1/books/zzz', status=500)
        assert r.json_body['success'] == False
        assert r.json_body['message'] == "invalid literal for int() with base 10: 'zzz'"

    def test_json_validation_error(self):
        app = self.testapp
        r = app.put('/api/v1/books/111', status=400)
        assert r.json_body['message'] == "Empty JSON body!"
        assert r.json_body['success'] == False

        book_id = 10
        fake_book = {'author': 'Blah'}
        r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=400)
        assert r.json_body['success'] == False
        assert 'Failed validating' in r.json_body['message']

    def test_succesful_put(self):
        app = self.testapp
        book_id = 123
        fake_book = {'id': book_id, 'title': 'Foo', 'author': 'Blah'}
        r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=200)


