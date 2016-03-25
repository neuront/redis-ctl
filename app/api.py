import os
import logging
from flask import Flask, g, request, session, render_template
from werkzeug.utils import import_string

import file_ipc
import render_utils
from models.base import init_db

blueprints = (
    'index',
    'pollings',
    'redis_panel',
    'command',
    'cluster',
)


def register_bp(app, module_name):
    import_name = '%s.bps.%s:bp' % (__package__, module_name)
    app.register_blueprint(import_string(import_name))


def init_logging(config):
    args = {'level': config.LOG_LEVEL}
    if config.LOG_FILE:
        args['filename'] = config.LOG_FILE
    args['format'] = config.LOG_FORMAT
    logging.basicConfig(**args)


class RedisApp(Flask):
    def __init__(self):
        Flask.__init__(self, 'RedisMunin', static_url_path='/static')

        self.jinja_env.globals['login_url'] = self.login_url()
        self.jinja_env.globals['render'] = render_template

        for u in dir(render_utils):
            if u.startswith('g_'):
                self.jinja_env.globals[u[2:]] = getattr(render_utils, u)
            elif u.startswith('f_'):
                self.jinja_env.filters[u[2:]] = getattr(render_utils, u)

        self.config_node_max_mem = 2048 * 1000 * 1000
        self.stats_client = None
        self.alarm_client = None

    def init_clients(self, config):
        init_logging(config)
        self.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
        self.config_node_max_mem = config.NODE_MAX_MEM
        self.debug = config.DEBUG == 1

        init_db(self)
        self.stats_client = self.init_stats_client(config)
        self.alarm_client = self.init_alarm_client(config)
        logging.info('Stats enabled: %s', self.stats_enabled())
        logging.info('Alarm enabled: %s', self.alarm_enabled())

    def register_blueprints(self):
        self.secret_key = os.urandom(24)
        self.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

        for bp in blueprints:
            register_bp(self, bp)
        if self.stats_enabled():
            register_bp(self, 'statistics')

        for bp in self.ext_blueprints():
            self.register_blueprint(bp)

        @self.before_request
        def init_global_vars():
            g.page = request.args.get('page', type=int, default=0)
            g.start = request.args.get('start', type=int, default=g.page * 20)
            g.limit = request.args.get('limit', type=int, default=20)
            g.user = self.get_user_from_session(session)
            g.lang = self.language()

    def get_user_from_session(self, session):
        return None

    def access_ctl_user_valid(self):
        return True

    def language(self):
        lang = request.headers.get('Accept-Language')
        if lang is None:
            return None
        try:
            return lang.split(';')[0].split('-')[0]
        except LookupError:
            return None

    def ext_blueprints(self):
        return []

    def login_url(self):
        return ''

    def polling_result(self):
        return file_ipc.read_details()

    def write_polling_details(self, redis_details, proxy_details):
        file_ipc.write_details(redis_details, proxy_details)

    def init_stats_client(self, config):
        if config.OPEN_FALCON and config.OPEN_FALCON['db']:
            from thirdparty.openfalcon import Client
            return Client(**config.OPEN_FALCON)
        return None

    def stats_enabled(self):
        return self.stats_client is not None

    def stats_query(self, addr, field, aggrf, span, now, interval):
        if self.stats_client is None:
            return []
        return self.do_stats_query(addr, field, aggrf, span, now, interval)

    def stats_write(self, addr, points):
        if self.stats_client is not None:
            self.do_stats_write(addr, points)

    def do_stats_query(self, addr, field, aggrf, span, now, interval):
        return self.stats_client.query(addr, field, aggrf, span, now, interval)

    def do_stats_write(self, addr, points):
        self.stats_client.write_points(addr, points)

    def init_alarm_client(self, config):
        if config.ALGALON and config.ALGALON['dsn']:
            from thirdparty.algalon_cli import AlgalonClient
            return AlgalonClient(**config.ALGALON)
        return None

    def alarm_enabled(self):
        return self.alarm_client is not None

    def send_alarm(self, message, trace):
        if self.alarm_client is not None:
            self.do_send_alarm(message, trace)

    def do_send_alarm(self, message, trace):
        self.alarm_client.send_alarm(message, trace)
