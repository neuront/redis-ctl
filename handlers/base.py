import os
import json
import types
import logging
import functools
import urllib
import urlparse
import flask
import werkzeug.exceptions
from werkzeug.utils import cached_property
from cStringIO import StringIO
from cgi import parse_qs
from eruhttp import EruException

import template
import file_ipc
import models.base
import models.user

app = flask.Flask('RedisControl')
app.secret_key = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


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

    def render(self, templ, **kwargs):
        return flask.Response(
            template.render(templ, user=self.user,
                            user_login_uri=self.login_url, **kwargs))

    @cached_property
    def user(self):
        if 'user' in self.session:
            return models.user.get_by_id(flask.session['user'])
        u = models.user.get_by_auth_key(self.idkey)
        if u is not None:
            self.set_user(u)
        return u

    def set_user(self, user):
        self.set_session('user', user.id)

    def del_user(self):
        self.set_session('user', None)

    @cached_property
    def idkey(self):
        return flask.request.cookies.get('idkey', None)

    @cached_property
    def login_url(self):
        return urlparse.urlunparse(urlparse.ParseResult(
            'http', 'openids-web.intra.hunantv.com', '/oauth/login', None,
            urllib.urlencode({
                'return_to': self.request.host_url + 'user/login_from_openid/',
                'days': '14',
            }), None))

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
            raise werkzeug.exceptions.Unauthorized()
        return f(request, *args, **kwargs)
    return wrapped


def demand_user_group(priv):
    privilege = getattr(models.user, 'PRIV_' + priv.upper())
    def wrapper(target):
        @functools.wraps(target)
        def wrapped(request, *args, **kwargs):
            if request.user is None:
                raise werkzeug.exceptions.Unauthorized()
            if privilege & request.user.priv_flags == 0:
                raise werkzeug.exceptions.Forbidden()
            return target(request, *args, **kwargs)
        return wrapped
    return wrapper


def send_file(filename, mimetype=None):
    return flask.send_file(filename, mimetype=mimetype, conditional=True)


def not_found():
    return flask.abort(404)
