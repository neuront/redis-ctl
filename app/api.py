import os
from flask import Flask, g, request, session, render_template
from werkzeug.utils import import_string

import stats
import file_ipc
import render_utils
from models.base import init_db

blueprints = (
    'index',
)


def register_bp(app, module_name):
    import_name = '%s.bps.%s:bp' % (__package__, module_name)
    app.register_blueprint(import_string(import_name))


class RedisCtlApp(Flask):
    def __init__(self, config):
        Flask.__init__(self, 'RedisMunin', static_url_path='/static')
        self.secret_key = os.urandom(24)
        self.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
        self.config['SQLALCHEMY_DATABASE_URI'] = sqla_uri

        init_db(self)

        for bp in blueprints:
            register_bp(self, bp)
        if self.stats_enabled():
            register_bp(self, 'statistics')

        for bp in ext_blueprints:
            self.register_blueprint(bp)

        self.jinja_env.globals['login_url'] = login_url
        self.jinja_env.globals['render'] = render_template

        for u in dir(render_utils):
            if u.startswith('g_'):
                self.jinja_env.globals[u[2:]] = getattr(render_utils, u)

        @self.before_request
        def init_global_vars():
            g.page = request.args.get('page', type=int, default=0)
            g.start = request.args.get('start', type=int, default=g.page * 20)
            g.limit = request.args.get('limit', type=int, default=20)
            g.user = get_user(session)

    def get_user_from_session(self, session):
        return None

    def ext_blueprints(self):
        return []

    def login_url(self):
        return ''

    def stats_client(self):
        return stats.client

    def stats_enabled(self):
        return self.stats_client() is not None

    def stats_query(self, addr, field, aggrf, span, now, interval):
        return stats.client.query(addr, field, aggrf, span, now, interval)

    def polling_result(self):
        return file_ipc.read_details()
