import re
import time
from flask import render_template, request

from app.bpbase import Blueprint
from app.utils import json_response

bp = Blueprint('stats', __name__, url_prefix='/stats')

PAT_HOST = re.compile('^[-.a-zA-Z0-9]+$')

REDIS_MAX_FIELDS = [
    'used_cpu_sys', 'used_cpu_user', 'connected_clients',
    'total_commands_processed', 'evicted_keys', 'expired_keys',
    'keyspace_misses', 'keyspace_hits',
]
REDIS_AVG_FIELDS = ['used_memory', 'used_memory_rss', 'response_time']
PROXY_MAX_FIELDS = ['connected_clients', 'mem_buffer_alloc',
                    'completed_commands', 'used_cpu_sys', 'used_cpu_user']
PROXY_AVG_FIELDS = ['command_elapse', 'remote_cost']


@bp.route('/redis')
def redis():
    return render_template('stats/redis.html', host=request.args['host'],
                           port=int(request.args['port']))


@bp.route('/proxy')
def proxy():
    return render_template('stats/proxy.html', host=request.args['host'],
                           port=int(request.args['port']))

def _parse_args(args):
    host = args['host']
    if not PAT_HOST.match(host):
        raise ValueError('Invalid hostname')
    port = int(args['port'])
    limit = min(int(args.get('limit', 100)), 500)
    interval = max(int(args.get('interval', 8)), 8)
    return host, port, limit, interval, limit * interval * 60


@bp.route('/fetchredis')
def fetch_redis():
    host, port, limit, interval, span = _parse_args(request.args)
    now = int(time.time())
    node = '%s:%d' % (host, port)
    result = {}

    for field in REDIS_AVG_FIELDS:
        result[field] = bp.app.stats_query(
            node, field, 'AVERAGE', span, now, interval)
    for field in REDIS_MAX_FIELDS:
        result[field] = bp.app.stats_query(
            node, field, 'MAX', span, now, interval)
    return json_response(result)


@bp.route('/fetchproxy')
def fetch_proxy():
    host, port, limit, interval, span = _parse_args(request.args)
    now = int(time.time())
    node = '%s:%d' % (host, port)
    result = {}

    for field in PROXY_MAX_FIELDS:
        result[field] = bp.app.stats_query(
            node, field, 'MAX', span, now, interval)
    for field in PROXY_AVG_FIELDS:
        result[field] = bp.app.stats_query(
            node, field, 'AVERAGE', span, now, interval)
    return json_response(result)
