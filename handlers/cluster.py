from socket import error as SocketError
import logging
import redistrib.command
from redistrib.clusternode import Talker
from redistrib.exceptions import RedisStatusError

import base
import template
import models.cluster
import models.task
import models.proxy
import models.node as nm
from models.base import db


@base.post_async('/cluster/launch')
def start_cluster(request):
    cluster_id = int(request.form['cluster_id'])
    try:
        nm.pick_and_launch(
            request.form['host'], int(request.form['port']), cluster_id,
            redistrib.command.start_cluster)
    except SocketError, e:
        logging.exception(e)
        models.cluster.remove_empty_cluster(cluster_id)
        raise ValueError('Node disconnected')


@base.post_async('/cluster/migrate_slots')
def migrate_slots(request):
    src_host = request.form['src_host']
    src_port = int(request.form['src_port'])
    dst_host = request.form['dst_host']
    dst_port = int(request.form['dst_port'])
    slots = [int(s) for s in request.form['slots'].split(',')]

    src = nm.get_by_host_port(src_host, src_port)

    task = models.task.ClusterTask(cluster_id=src.assignee_id,
                                   task_type=models.task.TASK_TYPE_MIGRATE)
    task.add_step('migrate', src_host=src.host, src_port=src.port,
                  dst_host=dst_host, dst_port=dst_port, slots=slots)
    db.session.add(task)


@base.post_async('/cluster/join')
def join_cluster(request):
    c = models.cluster.get_by_id(int(request.form['cluster_id']))
    if c is None or len(c.nodes) == 0:
        raise ValueError('no such cluster')
    task = models.task.ClusterTask(cluster_id=c.id,
                                   task_type=models.task.TASK_TYPE_JOIN)
    task.add_step('join', cluster_id=c.id, cluster_host=c.nodes[0].host,
                  cluster_port=c.nodes[0].port,
                  newin_host=request.form['host'],
                  newin_port=int(request.form['port']))
    db.session.add(task)


@base.post_async('/cluster/quit')
def quit_cluster(request):
    n = nm.get_by_host_port(request.post_json['host'],
                            int(request.post_json['port']))
    if n is None:
        raise ValueError('no such node')

    task = models.task.ClusterTask(cluster_id=n.assignee_id,
                                   task_type=models.task.TASK_TYPE_QUIT)
    for migr in request.post_json.get('migratings', []):
        task.add_step('migrate', src_host=n.host, src_port=n.port,
                      dst_host=migr['host'], dst_port=migr['port'],
                      slots=migr['slots'])
    task.add_step('quit', cluster_id=n.assignee_id, host=n.host, port=n.port)
    db.session.add(task)


@base.post_async('/cluster/batch')
def batch_tasks(request):
    c = models.cluster.get_by_id(request.post_json['cluster_id'])
    if c is None or len(c.nodes) == 0:
        raise ValueError('no such cluster')

    task = models.task.ClusterTask(
        cluster_id=c.id, task_type=models.task.TASK_TYPE_BATCH)
    has_step = False
    for n in request.post_json.get('migrs', []):
        has_step = True
        task.add_step(
            'migrate', src_host=n['src_host'], src_port=n['src_port'],
            dst_host=n['dst_host'], dst_port=n['dst_port'], slots=n['slots'])
    for n in request.post_json.get('quits', []):
        has_step = True
        task.add_step('quit', cluster_id=c.id, host=n['host'], port=n['port'])
    if has_step:
        db.session.add(task)


@base.post_async('/cluster/replicate')
def replicate(request):
    n = nm.get_by_host_port(
        request.form['master_host'], int(request.form['master_port']))
    if n is None or n.assignee_id is None:
        raise ValueError('unable to replicate')
    task = models.task.ClusterTask(cluster_id=n.assignee_id,
                                   task_type=models.task.TASK_TYPE_REPLICATE)
    task.add_step('replicate', cluster_id=n.assignee_id,
                  master_host=n.host, master_port=n.port,
                  slave_host=request.form['slave_host'],
                  slave_port=int(request.form['slave_port']))
    db.session.add(task)
