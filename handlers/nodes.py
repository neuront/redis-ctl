import config
import json
import logging
from socket import error as SocketError
from hiredis import ReplyError
from redistrib.clusternode import Talker

import file_ipc
import utils
import base
import models.node
import models.proxy
import models.task
import stats
from models.base import db

MAX_MEM_LIMIT = (64 * 1000 * 1000, config.NODE_MAX_MEM)


@base.get('/nodep/<host>/<int:port>')
def node_panel(request, host, port):
    node = models.node.get_by_host_port(host, port)
    if node is None:
        return base.not_found()
    detail = {}
    try:
        detail = file_ipc.read_details()['nodes'][
            '%s:%d' % (node.host, node.port)]
    except (IOError, ValueError, KeyError):
        pass
    return request.render(
        'node/panel.html', node=node, detail=detail,
        max_mem_limit=config.NODE_MAX_MEM,
        stats_enabled=stats.client is not None)


@base.post_async('/nodes/add')
def add_node(request):
    models.node.create_instance(
        request.form['host'], int(request.form['port']))


@base.post_async('/nodes/del')
def del_node(request):
    models.node.delete_free_instance(
        request.form['host'], int(request.form['port']))


@base.post_async('/nodes/fixmigrating')
def fix_node_migrating(request):
    n = models.node.get_by_host_port(request.form['host'],
                                     int(request.form['port']))
    if n is None or n.assignee is None:
        raise ValueError('no such node in cluster')
    task = models.task.ClusterTask(cluster_id=n.assignee.id,
                                   task_type=models.task.TASK_TYPE_FIX_MIGRATE)
    task.add_step('fix_migrate', host=n.host, port=n.port)
    db.session.add(task)


def _set_alert_status(n, request):
    if n is None:
        raise ValueError('no such node')
    n.suppress_alert = int(request.form['suppress'])
    db.session.add(n)
    db.session.flush()


@base.post_async('/set_alert_status/redis')
def set_redis_alert(request):
    _set_alert_status(models.node.get_by_host_port(
        request.form['host'], int(request.form['port'])), request)


@base.post_async('/set_alert_status/proxy')
def set_proxy_alert(request):
    _set_alert_status(models.proxy.get_by_host_port(
        request.form['host'], int(request.form['port'])), request)


@base.get_async('/nodes/get_masters')
def nodes_get_masters_info(request):
    try:
        masters, myself = utils.masters_detail(
            request.args['host'], int(request.args['port']))
        return base.json_result({
            'masters': masters,
            'myself': {
                'role': myself.role_in_cluster,
                'slots': len(myself.assigned_slots),
            },
        })
    except SocketError:
        return base.json_result({
            'masters': [],
            'myself': {'role': 'master', 'slots': 0},
        })


@base.post_async('/exec_command')
def node_exec_command(request):
    t = Talker(request.form['host'], int(request.form['port']))
    try:
        r = t.talk(*json.loads(request.form['cmd']))
    except ValueError as e:
        r = None if e.message == 'No reply' else ('-ERROR: ' + e.message)
    except ReplyError as e:
        r = '-' + e.message
    finally:
        t.close()
    return base.json_result(r)


@base.post_async('/nodes/set_max_mem')
def node_set_max_mem(request):
    max_mem = int(request.form['max_mem'])
    if not MAX_MEM_LIMIT[0] <= max_mem <= MAX_MEM_LIMIT[1]:
        raise ValueError('invalid max_mem size')
    host = request.form['host']
    port = int(request.form['port'])
    t = None
    try:
        t = Talker(host, port)
        m = t.talk('config', 'set', 'maxmemory', str(max_mem))
        if 'ok' != m.lower():
            raise ValueError('CONFIG SET maxmemroy redis %s:%d returns %s' % (
                host, port, m))
    except BaseException as exc:
        logging.exception(exc)
        raise
    finally:
        t.close()
