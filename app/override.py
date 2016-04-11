from flask import session, request, g, render_template, url_for

from core import RedisCtl, import_bp_string
import models.user


class App(RedisCtl):
    def __init__(self, config):
        RedisCtl.__init__(self, config)

        @self.errorhandler(403)
        @self.errorhandler(401)
        def error_handler(e):
            return render_template('errors/%s.html' % e.code), e.code

    def login_url(self):
        return url_for('.login')

    def ext_blueprints(self):
        return [import_bp_string('user')]

    def get_user(self):
        if 'user' in session:
            return models.user.get_by_id(session['user'])
        u = models.user.get_by_auth_key(request.cookies.get('idkey', None))
        if u is not None:
            self.set_user(u)
        return u

    def get_user_id(self):
        return g.user.id

    def default_user_id(self):
        return models.user.robot().id

    def render_user_by_id(self, user_id):
        return render_template('components/user/simple.html',
                               user=models.user.get_by_id(user_id))

    def access_ctl_user_valid(self):
        return g.user is not None and g.user.active

    def access_ctl_user_adv(self):
        return g.user is not None and g.user.is_adv

    def set_user(self, user):
        self.set_session('user', user.id)

    def del_user(self):
        self.set_session('user', None)

    def set_session(self, key, value):
        session[key] = value

    def get_session(self, key, default=None):
        return session.get(key, default)

    def init_container_client(self, config):
        from thirdparty.eru_utils import DockerClient
        return (DockerClient(config) if config.ERU and config.ERU['URL']
                else None)

    def init_stats_client(self, config):
        if (config.GRAPHITE and config.GRAPHITE.get('write_host') and
                config.GRAPHITE.get('query_host')):
            from thirdparty.graphite import Client
            return Client(**config.GRAPHITE)
        return None

    def init_alarm_client(self, config):
        return None
