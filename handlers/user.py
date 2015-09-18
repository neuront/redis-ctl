# encoding=utf-8

import re
import json
import urllib
import urllib2
import logging
import flask

import base
import models.user
from models.base import db

ATTRS_FIELDS = {'avatar', 'description'}
COOKIE_AGE = 86400 * 14
IDENT_PATTERN = re.compile(r'^[A-Za-z]\w{3,15}')


@base.app.errorhandler(401)
def unauthorized(_):
    return base.Request().render('errors/401.html'), 401


def _logout(request):
    request.del_user()
    resp = flask.redirect('/')
    resp.set_cookie('idkey', '')
    resp.set_cookie('username', '')
    resp.set_cookie('nickname', '')
    return resp


@base.get('/user/logout')
def logout(request):
    models.user.invalidate_auth_key(request.idkey)
    return _logout(request)


@base.get('/user/logoutall')
@base.demand_login
def logout_all(request):
    models.user.invalidate_auth_keys_of_user(request.user)
    return _logout(request)


@base.get('/user/me')
@base.demand_login
def display_my_info(request):
    return request.render('user/myinfo.html', who=request.user)


@base.get('/user/settings')
@base.demand_login
def user_settings(request):
    return request.render('user/settings.html')


@base.post_async('/user/change_attributes')
@base.demand_login
def user_attributes(request):
    if 'nickname' in request.form and len(request.form['nickname']) == 0:
        raise ValueError('Invalid nickname')
    for key, value in request.form.iteritems():
        if key in ATTRS_FIELDS:
            setattr(request.user, key, value)
    db.session.add(request.user)


@base.get('/user/profile/<username>')
@base.demand_user_group('user')
def display_profile(request, username):
    user = models.user.get_by_username(username)
    if user is None:
        return base.not_found()
    return request.render('user/info.html', who=user)


def _login_redirect(request, user):
    request.set_user(user)
    resp = flask.redirect('/')
    auth_key = models.user.UserAuthKey.gen_for(request.user)
    resp.set_cookie('idkey', auth_key.key, max_age=COOKIE_AGE)
    return resp


@base.get('/user/set_groups')
@base.demand_user_group('admin')
def user_set_groups_entry(request):
    return request.render('user/set_groups.html', users=models.user.list())


@base.get_async('/user/search')
@base.demand_user_group('user')
def search_user(request):
    user = models.user.get_by_username(request.args['username'])
    if user is None:
        return ''
    return base.json_result({
        'username': user.username,
        'nickname': user.nickname,
    })


@base.post_async('/user/do_set_groups')
@base.demand_user_group('admin')
def user_set_groups(request):
    user = models.user.get_by_username(request.form['user'])
    if user is None:
        raise ValueError('no such user')
    user.priv_flags = sum([getattr(models.user, 'PRIV_' + g.upper())
                           for g in set(request.form['groups'].split(','))])
    db.session.add(user)


@base.get('/user/login_from_openid/')
def login_from_openid(request):
    r = urllib2.urlopen('http://openids-web.intra.hunantv.com/oauth/profile/?'
                        + urllib.urlencode({'token': request.args['token']}))
    u = json.loads(r.read())
    user = models.user.get_by_openid(u['uid'])
    if user is None:
        username = IDENT_PATTERN.findall(u['uid'].replace('.', ''))
        if not username:
            logging.error('Invalid OpenID UID, detail: %s', json.dumps(u))
            return base.json_result(
                u'OpenID 返回了不合法的 UID, 请 RTX 联系 林喆', 400)
        user = models.user.User(username=username[0], openid=u['uid'],
                                priv_flags=models.user.PRIV_USER,
                                nickname=u['realname'])
        user.save()
        db.session.commit()
    return _login_redirect(request, user)


# ============== #
# debug shortcut #
# ============== #
if base.app.debug:
    @base.get('/user/request_login_as_admin')
    def debug_request_login_as_admin(request):
        u = models.user.get_by_username('_')
        if u is None:
            all_privs = (models.user.PRIV_USER | models.user.PRIV_ADMIN)
            u = models.user.User(
                username='_', priv_flags=all_privs, nickname='0', openid='_')
            u.save()
            db.session.commit()
        return _login_redirect(request, u)
