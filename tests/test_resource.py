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
    settings = {'pyramid_raml.apidef_path': os.path.join(DATA_DIR, 'test-api.raml')}
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
    assert r.json_body == {"message": "Book with id 111 could not be found.", "success": False}

    r = app.get('/api/v1/books/zzz', status=500)
    assert r.json_body == {"success": False, "message": "invalid literal for int() with base 10: 'zzz'"}
