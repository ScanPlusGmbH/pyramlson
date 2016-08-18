import re
import os
import venusian
import logging

from inspect import getmembers
from collections import namedtuple, defaultdict

from pyramid.path import AssetResolver
from pyramid.httpexceptions import (
    HTTPBadRequest,
    HTTPInternalServerError,
    HTTPNoContent,
)
from pyramid.interfaces import IExceptionResponse

from .apidef import IRamlApiDefinition
from .utils import prepare_json_body, render_view

log = logging.getLogger(__name__)


DEFAULT_METHOD_MAP = {
    'get': 200,
    'post': 200,
    'put': 201,
    'delete': 204,
    'options': 200,
    'patch': 200,
}

MethodRestConfig = namedtuple('MethodRestConfig', [
    'http_method',
    'permission',
    'returns'
])


MARKER = object()

class api_method(object):

    def __init__(self, http_method, permission=None, returns=None):
        """Configure a resource method corresponding with a RAML resource path

        This decorator must be used to declare REST resources.

        :param http_method: The HTTP method this method maps to.

        :param permission: Permission for this method.

        :param returns: A custom HTTP code to return in case of success.

            Configure the HTTP code to return when the method call was successful.
            Per default the codes are expected to match the configured HTTP method:
                - GET/POST/PATCH: 200
                - PUT: 201
                - DELETE: 204

        """
        self.http_method = http_method
        self.permission = permission
        self.returns = returns if returns is not None else DEFAULT_METHOD_MAP[self.http_method]

    def __call__(self, method):
        method._rest_config = MethodRestConfig(self.http_method,
                self.permission,
                self.returns)
        return method


class api_service(object):
    """Configures a resource by its REST path.

    This decorator configures a class as a REST resource. All endpoints
    must be defined in a RAML file.
    """

    def __init__(self, resource_path):
        log.debug("Resource path: {}".format(resource_path))
        self.resource_path = resource_path
        self.resources = []

    def callback(self, scanner, name, cls):
        config = scanner.config.with_package(self.module)
        apidef = config.registry.queryUtility(IRamlApiDefinition)
        self.create_route(config)
        log.debug("registered routes with base route '{}'".format(apidef.base_path))
        self.create_views(config)

    def create_route(self, config):
        log.debug("Creating route for {}".format(self.resource_path))
        supported_methods = []
        apidef = config.registry.queryUtility(IRamlApiDefinition)
        route_name = None

        # Find all methods for this resource path
        for resource in apidef.get_resources(self.resource_path):
            if route_name is None:
                path = self.resource_path
                if apidef.base_path:
                    path = "{}{}".format(apidef.base_path, path)
                route_name = "{}-{}".format(resource.display_name, path)

            method = resource.method.upper()
            self.resources.append((route_name, method, resource, None))
            supported_methods.append(method)

        # Add one route for all the methods at this resource path
        if supported_methods:
            log.debug("Registering route with path {}".format(path))
            config.add_route(route_name, path, factory=self.cls)
            # add a default OPTIONS view if none was defined by the resource
            opts_meth = 'OPTIONS'
            if opts_meth not in supported_methods:
                methods = supported_methods + [opts_meth]
                self.resources.append((route_name, 'OPTIONS', resource, create_options_view(methods)))

    def create_views(self, config):
        for (route_name, method, resource, default_view) in self.resources:
            log.debug("Creating view {} {}".format(route_name, method))
            if default_view:
                config.add_view(default_view,
                    route_name=route_name,
                    request_method=method)
            else:
                (view, permission) = self.create_view(resource)
                log.debug("Registering view {} for route name '{}', resource '{}', method '{}'".format(view, route_name, resource, method))
                config.add_view(view,
                        route_name=route_name,
                        request_method=method,
                        permission=permission)

    def __call__(self, cls):
        self.cls = cls
        info = venusian.attach(cls, self.callback, 'pyramid', depth=1)
        self.module = info.module
        return cls

    def create_view(self, resource):
        (meth, cfg) = self.get_service_class_method(resource)
        log.debug("Got method {} for resource {}".format(meth, resource))
        if not meth:
            raise ValueError("Could not find a method in class {} suitable for resource {}.".format(self.cls, resource))
        def view(context, request):
            required_params = [context]
            optional_params = dict()
            # URI parameters have the highest prio
            if resource.uri_params:
                for param in resource.uri_params:
                    param_value = request.matchdict[param.name]
                    validate_param(param, param_value)
                    # pyramid router makes sure the URI params are all
                    # set, otherwise the view isn't called all, because
                    # a NotFound error is triggered before the request
                    # can be routed to this view
                    required_params.append(param_value)
            # If there's a body defined - include it before traits or query params
            if resource.body:
                required_params.append(prepare_json_body(request, resource.body))
            if resource.query_params:
                for param in resource.query_params:
                    param_value = request.params.get(param.name, MARKER)
                    if param_value is not MARKER:
                        validate_param(param, param_value)
                    else:
                        param_value = param.default
                    # query params are always named (i.e. not positional)
                    # so they effectively become keyword agruments in a
                    # method call, we just make sure they are present
                    # in the request if marked as 'required'
                    if param.required and param.name not in request.params:
                        raise HTTPBadRequest("{} ({}) is required".format(param.name, param.type))
                    else:
                        optional_params[param.name] = param_value
            result = meth(*required_params, **optional_params)
            return render_view(request, result, cfg.returns)

        return (view, cfg.permission)

    def get_service_class_method(self, resource):
        rel_path = resource.path[len(self.resource_path):]
        log.debug("Relative path for {}: '{}'".format(resource, rel_path))
        http_method = resource.method.lower()
        for (name, member) in getmembers(self.cls):
            if not hasattr(member, '_rest_config'):
                continue
            cfg = member._rest_config
            if (cfg.http_method.lower() == http_method) and callable(member):
                return (member, cfg)
        return (None, None)

def create_options_view(supported_methods):
    def view(context, request):
        response = HTTPNoContent()
        response.headers['Access-Control-Allow-Methods'] =\
            ', '.join(supported_methods)
        return response
    return view


def includeme(config):
    """Configure basic RAML REST settings for a Pyramid application.

    You should not call this function directly, but use
    :py:func:`pyramid.config.Configurator.include` to initialise
    the RAML routing.

    .. code-block:: python
       :linenos:
       config = Configurator()
       config.include('pyramlson')
    """
    from pyramlson.apidef import RamlApiDefinition, IRamlApiDefinition
    settings = config.registry.settings
    settings['pyramlson.debug'] = \
            settings.get('debug_all') or \
            settings.get('pyramid.debug_all') or \
            settings.get('pyramlson.debug')
    config.add_view('pyramlson.error.generic', context=Exception, renderer='json')
    config.add_view('pyramlson.error.http_error', context=IExceptionResponse, renderer='json')
    config.add_notfound_view('pyramlson.error.notfound', renderer='json')
    config.add_forbidden_view('pyramlson.error.forbidden', renderer='json')

    if 'pyramlson.apidef_path' not in settings:
        raise ValueError("Cannot create RamlApiDefinition without a RAML file.")
    res = AssetResolver()
    apidef_path = res.resolve(settings['pyramlson.apidef_path'])
    apidef = RamlApiDefinition(apidef_path.abspath())
    config.registry.registerUtility(apidef, IRamlApiDefinition)


def validate_param(param, value):
    # FIXME: add more checks
    if param.type == 'integer':
        try:
            int(value)
        except ValueError as e:
            raise HTTPBadRequest("Malformed parameter '{}', expected integer, got '{}'".format(param.name, value))
    if param.type == 'string':
        if param.enum and value not in param.enum:
            raise HTTPBadRequest("Malformed parameter '{}', expected one of {}, got '{}'".format(param.name, ', '.join(param.enum), value))
        if param.pattern:
            result = re.search(param.pattern, value)
            if not result:
                raise HTTPBadRequest("Malformed parameter '{}', expected pattern {}, got '{}'".format(param.name, param.pattern, value))
        if param.min_length and len(value) < param.min_length:
            msg = "Malformed parameter '{}', expected minimum length is {}, got {}"
            raise HTTPBadRequest(msg.format(
                param.name,
                param.min_length,
                len(value)
            ))
        if param.max_length and len(value) > param.max_length:
            msg = "Malformed parameter '{}', expected maximum length is {}, got {}"
            raise HTTPBadRequest(msg.format(
                param.name,
                param.max_length,
                len(value)
            ))
__all__ = ['api_method', 'api_service']
