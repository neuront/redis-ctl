import os
import json
import types
import logging
import functools
import flask
import werkzeug.exceptions
from werkzeug.utils import cached_property
from cStringIO import StringIO
from cgi import parse_qs
from eruhttp import EruException

import template
import file_ipc
import models.base
from app.api import RedisCtlApp
import config

app = RedisCtlApp(config)


# http://stackoverflow.com/a/11163649
class _WSGICopyBody(object):
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        try:
            length = int(environ.get('CONTENT_LENGTH', '0'))
        except ValueError:
            length = 0

        body = environ['wsgi.input'].read(length)
        environ['body_copy'] = body
        environ['wsgi.input'] = StringIO(body)

        return self.application(environ, self._sr_callback(start_response))

    def _sr_callback(self, start_response):
        def callback(status, headers, exc_info=None):
            start_response(status, headers, exc_info)
        return callback

app.wsgi_app = _WSGICopyBody(app.wsgi_app)


def json_result(obj, status_code=200):
    r = flask.Response(template.f_tojson(obj), mimetype='application/json')
    r.status_code = status_code
    return r


def strip_irregular_space(s):
    return s.replace('\t', '').replace('\r', '')


class Request(object):
    def __init__(self):
        self.request = flask.request
        self.args = flask.request.args
        self.session = flask.session

    @cached_property
    def post_body(self):
        return self.request.environ['body_copy']

    @cached_property
    def post_body_text(self):
        return unicode(strip_irregular_space(self.post_body), 'utf-8')

    @cached_property
    def post_json(self):
        return json.loads(self.post_body_text)

    @cached_property
    def form(self):
        try:
            return {k: unicode(strip_irregular_space(v[0]), 'utf-8')
                    for k, v in parse_qs(self.post_body).iteritems()}
        except (ValueError, TypeError, AttributeError, LookupError):
            return {}

    @cached_property
    def lang(self):
        try:
            return self.request.headers.get(
                'Accept-Language').split(';')[0].split('-')[0]
        except LookupError:
            return None

    def render(self, templ, **kwargs):
        return flask.Response(template.render(templ, lang=self.lang, **kwargs))

    def set_session(self, key, value):
        self.session[key] = value

    def get_session(self, key, default=None):
        return self.session.get(key, default)

    def del_session(self, key):
        if key in self.session:
            del self.session[key]

    def forbid(self):
        raise werkzeug.exceptions.Forbidden()


def route(uri, method):
    def wrapper(f):
        @app.route(uri, methods=[method])
        @functools.wraps(f)
        def handle_func(*args, **kwargs):
            return f(Request(), *args, **kwargs)
        return handle_func
    return wrapper


def route_async(uri, method, commit_db):
    def wrapper(f):
        @route(uri, method)
        @functools.wraps(f)
        def g(request, *args, **kwargs):
            try:
                r = f(request, *args, **kwargs) or ''
                if commit_db:
                    models.base.db.session.commit()
                    file_ipc.write_nodes_proxies_from_db()
                return r
            except KeyError, e:
                r = dict(reason='missing argument', missing=e.message)
            except UnicodeEncodeError, e:
                r = dict(reason='invalid input encoding')
            except ValueError, e:
                r = dict(reason=e.message)
            except EruException, e:
                logging.exception(e)
                r = dict(reason='eru fail', detail=e.message)
            except StandardError, e:
                logging.error('UNEXPECTED ERROR')
                logging.exception(e)
                return json_result(
                    {'reason': 'unexpected', 'msg': e.message}, 500)
            return json_result(r, 400)
        return g
    return wrapper

get = lambda uri: route(uri, 'GET')
get_async = lambda uri: route_async(uri, 'GET', False)
post_async = lambda uri: route_async(uri, 'POST', True)


def paged(uri, page=1):
    def wrapper(f):
        @get(uri)
        @functools.wraps(f)
        def origin(request, *args, **kwargs):
            return f(request, 0, *args, **kwargs)

        return get(uri + '/<int:page>')(types.FunctionType(
            f.func_code, f.func_globals, f.__name__ + '__paged',
            f.func_defaults, f.func_closure))
    return wrapper


def demand_login(f):
    @functools.wraps(f)
    def wrapped(request, *args, **kwargs):
        if request.user is None:
            return werkzeug.exceptions.Unauthorized()
        return f(request, *args, **kwargs)
    return wrapped


def send_file(filename, mimetype=None):
    return flask.send_file(filename, mimetype=mimetype, conditional=True)


def not_found():
    return flask.abort(404)
