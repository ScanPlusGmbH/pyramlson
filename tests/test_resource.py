import os
import pytest
from webtest import TestApp
from pyramid.config import Configurator
from pyramid.testing import DummyRequest
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy

from .base import DATA_DIR
from .resource import BOOKS

def make_default_config():
    settings = {
        'pyramid_raml.apidef_path': os.path.join(DATA_DIR, 'test-api.raml'),
        'pyramid_raml.debug': 'true'
    }
    config = Configurator(settings=settings, introspection=True)
    config.include('pyramid_raml')
    return config

def make_app(config):
    return TestApp(config.make_wsgi_app())

def test_return_values():
    config = make_default_config()
    config.scan('.resource')
    app = make_app(config)
    r = app.get('/api/v1/books', status=200)
    assert r.json_body == list(BOOKS.values())

    r = app.get('/api/v1/books/123', status=200)
    assert r.json_body == BOOKS[123]

    r = app.get('/api/v1/books/456', status=200)
    assert r.json_body == BOOKS[456]

    r = app.get('/api/v1/books/111', status=404)
    assert r.json_body['success'] == False
    assert r.json_body['message'] == "Book with id 111 could not be found."

    r = app.get('/api/v1/books/zzz', status=500)
    assert r.json_body['success'] == False
    assert r.json_body['message'] == "invalid literal for int() with base 10: 'zzz'"

    r = app.put('/api/v1/books/111', status=400)
    assert r.json_body['message'] == "Empty JSON body!"
    assert r.json_body['success'] == False

    book_id = 10
    fake_book = {'id': book_id, 'title': 'Foo', 'author': 'Blah'}
    r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=404)
    assert r.json_body['success'] == False
    assert r.json_body['message'] == "Book with id {} could not be found.".format(book_id)

    book_id = 123
    fake_book = {'id': book_id, 'title': 'Foo', 'author': 'Blah'}
    r = app.put_json('/api/v1/books/{}'.format(book_id), params=fake_book, status=200)

    r = app.options('/api/v1/books', status=204)
    methods = [meth for meth in r.headers['Access-Control-Allow-Methods'].split(", ")]
    assert 'GET' in methods
    assert 'POST' in methods
    assert 'OPTIONS' in methods

#def test_foo():
#    config = make_default_config()
#    config.scan('.resource')
#    app = make_app(config)
