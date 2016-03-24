from flask import request
from hiredis import ReplyError
from redistrib.clusternode import Talker

from app.utils import json_response
from app.bpbase import Blueprint

bp = Blueprint('command', __name__, url_prefix='/cmd')


def _simple_cmd(host, port, *command):
    status = 200
    try:
        with Talker(host, port) as t:
            try:
                r = t.talk(*command)
            except ReplyError as e:
                r = {'reason': e.message}
                status = 400
    except IOError:
        status = 400
        r = {'reason': 'not reachable'}
    return json_response(r, status)

@bp.route('/info')
def exec_info():
    return _simple_cmd(request.args['host'], int(request.args['port']), 'info')

@bp.route('/cluster_nodes')
def exec_cluster_nodes():
    return _simple_cmd(request.args['host'], int(request.args['port']),
                       'cluster', 'nodes')
