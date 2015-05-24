from collections import OrderedDict
from pyramid.security import (
    Allow,
    ALL_PERMISSIONS,
    DENY_ALL,
)

from pyramid_raml import api_service, api_method

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

class BookNotFound(Exception):
    code = 404

@api_service('/books')
class BooksResource(object):

    __acl__ = [
        (Allow, 'api-user', ('view', 'create', 'update')),
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

    @api_method('get', permission='view', subpath='/{bookId}', raises=(BookNotFound,))
    def get_one(self, book_id):
        return get_book(book_id)

    @api_method('put',
            permission='update',
            subpath='/{bookId}',
            raises=(BookNotFound,),
            returns=201)
    def update(self, book_id, data):
        book = get_book(book_id)
        book.update(data)
        return book

    @api_method('put',
            permission='delete',
            subpath='/{bookId}',
            raises=(BookNotFound,),
            returns=204)
    def delete(self, book_id):
        book = get_book(book_id)
        BOOKS.pop(book["id"])