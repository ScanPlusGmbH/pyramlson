import logging
import traceback
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import unauthenticated_userid


log = logging.getLogger(__name__)


def err_dict(message):
    return dict(success=False, message=message)

def generic(context, request):
    log.error("error.generic -- context: \"{}\"".format(context))
    tb = ''.join(traceback.format_exception(*request.exc_info))
    log.error("error.generic -- traceback: \"{}\"".format(tb))
    request.response.status_int = 500
    try:
        response = err_dict(context.args[0])
    except IndexError:
        response = err_dict('Unknown error')
    if request.registry.settings.get('pyramlson.debug'):
        response['traceback'] = tb
    return response


def http_error(context, request):
    log.info("error.http_error -- context: \"{}\"".format(context))
    request.response.status = context.status
    for (header, value) in context.headers.items():
        if header in {'Content-Type', 'Content-Length'}:
            continue
        request.response.headers[header] = value
    if context.message:
        return err_dict(context.message)
    else:
        return err_dict(context.status)


def notfound(context, request):
    log.info("error.notfound -- context: \"{}\"".format(context))
    message = 'Resource not found'
    if isinstance(context, HTTPNotFound):
        if context.content_type == 'application/json':
            return context
        elif context.detail:
            message = context.detail
    request.response.status_int = 404
    return err_dict(message)


def forbidden(request):
    log.info("error.forbidden")
    if unauthenticated_userid(request):
        request.response.status_int = 403
        return err_dict('You are not allowed to perform this action.')
    else:
        request.response.status_int = 401
        return err_dict('You must login to perform this action.')
