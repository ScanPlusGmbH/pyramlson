# coding: utf-8
"""
Pyramlson utilities
"""
import re
import jsonschema
from email.utils import parsedate
from datetime import datetime

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.renderers import render_to_response

from .apidef import IRamlApiDefinition


def prepare_json_body(request, body):
    """ Convert request body to json and validate it. """
    if not request.body:
        raise HTTPBadRequest(u"Empty body!")
    try:
        data = request.json_body
    except ValueError:
        raise HTTPBadRequest(u"Invalid JSON body: {}".format(request.body))
    apidef = request.registry.queryUtility(IRamlApiDefinition)
    schema = apidef.get_schema(body)
    if schema:
        try:
            jsonschema.validate(
                data,
                schema,
                format_checker=jsonschema.draft4_format_checker
            )
        except jsonschema.ValidationError as err:
            if request.registry.settings.get('pyramlson.debug'):
                raise HTTPBadRequest(str(err))
            else:
                raise HTTPBadRequest(err.message)
    return data


def render_view(request, data, status_code):
    """ Render data to response using the correct response status code """
    response = request.response
    response.status_int = status_code
    try:
        return render_to_response('json', data, request=request, response=response)
    except TypeError:
        # 1.5.7 compat
        return render_to_response('json', data, request=request)


def validate_and_convert(param, value):
    converter = CONVERTERS.get(param.type)
    if converter:
        return converter(param, value)
    return value

def _bool_converter(param, value):
    if type(value) is bool:
        return value
    if value.lower() not in ('true', 'false'):
        msg = "Malformed boolean parameter '{}', expected 'true' or 'false', got '{}'".format(
            param.name,
            value
        )
        raise HTTPBadRequest(msg)
    return value.lower() == 'true'

def _number_converter(param, value):
    if type(value) in (int, float):
        if type(value) is float and param.type == 'integer':
            msg = "Malformed parameter '{}', expected integer, got float: '{}'".format(
                param.name,
                value
            )
            raise HTTPBadRequest(msg)
        return value
    converted = None
    try:
        caster = int
        if param.type == 'number' and '.' in value:
            caster = float
        converted = caster(value)
    except ValueError:
        msg = "Malformed parameter '{}', expected a syntactically valid {}, got '{}'".format(
            param.name,
            param.type,
            value
        )
        raise HTTPBadRequest(msg)
    if param.minimum and converted < param.minimum:
        msg = "Parameter '{}' is too small, expected at least {}, got {}".format(
            param.name,
            param.minimum,
            converted
        )
        raise HTTPBadRequest(msg)
    if param.maximum and converted > param.maximum:
        msg = "Parameter '{}' is too large, expected at most {}, got {}".format(
            param.name,
            param.maximum,
            converted
        )
        raise HTTPBadRequest(msg)

    return converted

def _string_converter(param, value):
    if param.enum and value not in param.enum:
        msg = "Malformed parameter '{}', expected one of {}, got '{}'".format(
            param.name,
            ', '.join(param.enum),
            value
        )
        raise HTTPBadRequest(msg)
    if param.pattern:
        result = re.search(param.pattern, value)
        if not result:
            msg = "Malformed parameter '{}', expected pattern {}, got '{}'".format(
                param.name,
                param.pattern,
                value
            )
            raise HTTPBadRequest(msg)
    if param.min_length and len(value) < param.min_length:
        msg = "Malformed parameter '{}', expected minimum length is {}, got {}".format(
            param.name,
            param.min_length,
            len(value)
        )
        raise HTTPBadRequest(msg)
    if param.max_length and len(value) > param.max_length:
        msg = "Malformed parameter '{}', expected maximum length is {}, got {}".format(
            param.name,
            param.max_length,
            len(value)
        )
        raise HTTPBadRequest(msg)
    return value

def _date_converter(param, value):
    if type(param) is datetime:
        return value
    parsed = parsedate(value)
    if parsed is None:
        # parsedate returns None if the date string could not be parsed
        msg = "Malformed parameter '{}', expected RFC 2616 formatted date, got {}".format(
            param.name,
            value
        )
        raise HTTPBadRequest(msg)
    try:
        return datetime(*parsed[:6])
    except ValueError as err:
        msg = "Malformed parameter '{}': {}".format(
            param.name,
            err
        )
        raise HTTPBadRequest(msg)


CONVERTERS = {
    'bool': _bool_converter,
    'integer': _number_converter,
    'number': _number_converter,
    'string': _string_converter,
    'date': _date_converter,
}
