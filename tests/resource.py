from pyramid.security import (
    Allow,
    ALL_PERMISSIONS,
    DENY_ALL,
)

from pyramid_raml import api_service, api_method

BOOKS = [{
    "id": 123,
    "title": "Dune",
    "author": "Frank Herbert",
    "isbn": "98765"
}, {
    "id": 456,
    "title": "Hyperion Cantos",
    "author": "Dan Simmons",
    "isbn": "56789"
}]

@api_service('/books')
class BooksResource(object):

    __acl__ = [
        (Allow, 'api-user', ('view', 'create')),
        (Allow, 'admin', ALL_PERMISSIONS),
        DENY_ALL,
    ]

    def __init__(self, request):
        self.request = request

    @api_method('post', permission='create')
    def create_record(self, data):
        return dict(success=True, message='Book created')

    @api_method('get', permission='view')
    def get_all(self, sort_by='id', sort_reversed=False, offset=0, limit=10):
        return BOOKS

    @api_method('get', permission='view', subpath='/{bookId}')
    def get_one(self, book_id):
        for book in BOOKS:
            if book_id == book["id"]:
                return book
        return None
