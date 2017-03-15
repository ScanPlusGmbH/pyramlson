from datetime import datetime
from collections import OrderedDict

from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import (
    Allow,
    ALL_PERMISSIONS,
    DENY_ALL,
)

from pyramlson import api_service, api_method


class Book(object):
    """ A simple book class """

    def __init__(self, id, title, author, isbn=None):
        self.id = id
        self.title = title
        self.author = author
        selfisbn = isbn

    @classmethod
    def from_dict(klass, id, data):
        return klass(id, data['title'], data['author'], data.get('isbn', None))

    @classmethod
    def from_etree(klass, id, tree):
        return klass(id, data['title'], data['author'], data.get('isbn', None))

BOOKS = OrderedDict()
BOOKS[123] = {"id": 123,
    "title": "Dune",
    "author": "Frank Herbert",
    "isbn": "98765"
}
BOOKS[456] = {
    "id": 456,
    "title": "Hyperion Cantos",
    "author": "Dan Simmons",
    "isbn": "56789"
}

def get_book(book_id):
    bid = int(book_id)
    if bid not in BOOKS:
        raise BookNotFound("Book with id {} could not be found.".format(book_id))
    return BOOKS[bid]

class BookNotFound(HTTPNotFound):
    pass

@api_service('/books')
class BooksResource(object):

    __acl__ = [
        (Allow, 'api-user-reader', ('view', )),
        (Allow, 'api-user-writer', ('view', 'create', 'update')),
        (Allow, 'admin', ALL_PERMISSIONS),
        DENY_ALL,
    ]

    def __init__(self, request):
        self.request = request

    @api_method('post', permission='create')
    def create_record(self, data):
        bid = int(data["id"])
        BOOKS[bid] = data
        return BOOKS[bid]

    @api_method('get', permission='view')
    def get_all(self, sort_by='id', sort_reversed=False, offset=0, limit=10):
        return list(BOOKS.values())


@api_service('/books/{bookId}')
class BookResource(object):

    __acl__ = [
        (Allow, 'api-user-reader', ('view', )),
        (Allow, 'api-user-writer', ('view', 'create', 'update')),
        (Allow, 'admin', ALL_PERMISSIONS),
        DENY_ALL,
    ]

    def __init__(self, request):
        self.request = request

    @api_method('get', permission='view')
    def get_one(self, book_id):
        return get_book(book_id)

    @api_method('put',
            permission='update',
            returns=200)
    def update(self, book_id, data):
        book = get_book(book_id)
        book.update(data)
        return dict(success=True)

    @api_method('delete',
            permission='delete',
            returns=204)
    def delete(self, book_id):
        book = get_book(book_id)
        BOOKS.pop(book["id"])


@api_service('/books/some/other/things')
class SomeOtherThings(object):

    def __init__(self, request):
        self.request = request

    @api_method('get')
    def things(self, thing_type=None):
        return dict(thing_type=thing_type)


@api_service('/parametrized')
class ConvertMyParams(object):

    def __init__(self, request):
        self.request = request

    @api_method('get')
    def parametrized(self, max_string='', min_string='xy',
                     choice_string='foo', pattern_string='ABCD54321',
                     some_number=5.9, min_max_number=42,
                     min_max_integer=30, some_bool=False,
                     missing_default='defined in method!',
                     some_date=datetime(2017, 1, 1, 1, 1, 1)):
        ret = locals()
        del ret['self']
        return ret

