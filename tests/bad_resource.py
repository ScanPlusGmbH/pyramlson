from pyramlson import api_service, api_method

@api_service('/books')
class BadResource(object):

    def __init__(self, request):
        self.request = request
