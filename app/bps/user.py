# encoding=utf-8

import re
import functools
from flask import abort, request, g, render_template, session, redirect
import flask
import config
from flask_oauthlib.client import OAuth

from app.bpbase import Blueprint
from app.utils import json_response
from models.base import db
import models.user

bp = Blueprint('user', __name__, url_prefix='/user')
ATTRS_FIELDS = {'avatar', 'description'}
COOKIE_AGE = 86400 * 14
IDENT_PATTERN = re.compile(r'^\w{4,16}')

oauth = OAuth(flask.current_app)
remote = oauth.remote_app(
    'sso',
    consumer_key=config.OAUTH2_CLIENT_ID,
    consumer_secret=config.OAUTH2_CLIENT_SECRET,
    request_token_params={'scope': 'email'},
    base_url=config.OAUTH2_BASE_URL,
    request_token_url=None,
    access_token_url=config.OAUTH2_ACCESS_TOKEN_URL,
    authorize_url=config.OAUTH2_AUTHORIZE_URL,
)

def _logout():
    session['user'] = None
    resp = redirect('/')
    resp.set_cookie('idkey', '')
    resp.set_cookie('username', '')
    resp.set_cookie('nickname', '')
    return resp


@bp.route('/logout')
def logout():
    return _logout()


@bp.route('/logoutall')
def logout_all():
    models.user.invalidate_auth_keys_of_user(g.user)
    db.session.commit()
    return _logout()


@bp.route('/me')
def display_my_info():
    if g.user is None:
        return abort(401)
    return render_template('user/myinfo.html', who=g.user)


@bp.route('/settings')
def user_settings():
    if g.user is None:
        return abort(401)
    return render_template('user/settings.html')


@bp.route_post_json('/change_attributes')
def user_attributes():
    if 'nickname' in request.form and len(request.form['nickname']) == 0:
        raise ValueError('Invalid nickname')
    for key, value in request.form.iteritems():
        if key in ATTRS_FIELDS:
            setattr(g.user, key, value)
    db.session.add(g.user)


@bp.route('/profile/<username>')
def display_profile(username):
    user = models.user.get_by_username(username)
    if user is None:
        return abort(404)
    return render_template('user/info.html', who=user)


def _login_redirect(user):
    session['user'] = user.id
    resp = redirect('/')
    auth_key = models.user.UserAuthKey.gen_for(user)
    resp.set_cookie('idkey', auth_key.key, max_age=COOKIE_AGE)
    return resp


def demand_user_group(privilege):
    def wrapper(target):
        @functools.wraps(target)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return abort(401)
            if privilege & g.user.priv_flags == 0:
                return abort(403)
            return target(*args, **kwargs)
        return wrapped
    return wrapper


@bp.route('/set_groups')
@demand_user_group(models.user.PRIV_ADMIN)
def user_set_groups_entry():
    return request.render('user/set_groups.html', users=models.user.list())


@bp.route('/user/search')
def search_user():
    user = models.user.get_by_username(request.args['username'])
    if user is None:
        return ''
    return json_response({
        'username': user.username,
        'nickname': user.nickname,
    })


@bp.route_post_json('/do_set_groups')
@demand_user_group(models.user.PRIV_ADMIN)
def user_set_groups():
    user = models.user.get_by_username(request.form['user'])
    if user is None:
        raise ValueError('no such user')
    user.priv_flags = sum([getattr(models.user, 'PRIV_' + g.upper())
                           for g in set(request.form['groups'].split(','))])
    db.session.add(user)


@remote.tokengetter
def get_oauth_token():
    return flask.session.get('remote_oauth')


@bp.route('/authorized')
def authorized():
    #TODO why!!!!!
    flask.session['sso_oauthredir'] = flask.url_for('.authorized', _external=True)
    resp = remote.authorized_response()
    if resp is None:
        print request.args['error_reason'], request.args['error_description']
        flask.abort(400)
    flask.session['remote_oauth'] = (resp['access_token'], '')
    return flask.redirect(flask.url_for('.login'))


@bp.route('/user/login_from_sso')
def login():
    if 'remote_oauth' in flask.session:
        resp = remote.get('me')
        user_info = resp.data
        user = models.user.get_by_openid(user_info['id'])
        if not user:
            admin = models.user.PRIV_USER if not int(user_info['privilege']) else models.user.PRIV_ADMIN
            user = models.user.User(username=user_info['name'], openid=user_info['id'],
                                    priv_flags=admin,
                                    nickname=user_info['real_name'])
            user.save()
            db.session.commit()
        return _login_redirect(user)
    return remote.authorize(
        callback=flask.url_for('.authorized', _external=True)
    )


# ============== #
# debug shortcut #
# ============== #

if config.DEBUG:
    @bp.route('/request_login_as_admin')
    def debug_request_login_as_admin():
        u = models.user.get_by_username('_')
        if u is None:
            all_privs = (models.user.PRIV_USER | models.user.PRIV_ADMIN)
            u = models.user.User(
                username='_', priv_flags=all_privs, nickname='0', openid='_')
            u.save()
            db.session.commit()
        return _login_redirect(u)
