import redistrib
from flask import render_template, abort, request, g

from app.bpbase import Blueprint
from app.utils import json_response
from app.render_utils import f_strftime
from models.base import db
import models.node
import models.task

bp = Blueprint('task', __name__, url_prefix='/task')


@bp.before_request
def access_control():
    if not bp.app.access_ctl_user_valid():
        abort(403)


@bp.route('/list_all')
def list_all_tasks():
    return render_template(
        'cluster/tasks_all.html', page=g.page,
        tasks=models.task.get_all_tasks(g.page * 50, 50))


@bp.route('/list_cluster/<int:cluster_id>')
def list_cluster_tasks(cluster_id):
    c = models.cluster.get_by_id(cluster_id)
    if c is None:
        return abort(404)
    return render_template('cluster/tasks.html', page=g.page,
                           tasks=c.get_tasks(g.page * 50, 50))


@bp.route_post_json('/fix_redis')
def fix_redis_migrating():
    n = models.node.get_by_host_port(request.form['host'],
                                     int(request.form['port']))
    if n is None or n.assignee_id is None:
        raise ValueError('no such node in cluster')
    task = models.task.ClusterTask(cluster_id=n.assignee_id,
                                   task_type=models.task.TASK_TYPE_FIX_MIGRATE)
    task.add_step('fix_migrate', host=n.host, port=n.port)
    db.session.add(task)


@bp.route_post_json('/fix_cluster')
def fix_cluster_migrating():
    c = models.cluster.get_by_id(int(request.form['cluster_id']))
    if c is None:
        raise ValueError('no such cluster')
    masters = redistrib.command.list_masters(
        c.nodes[0].host, c.nodes[0].port)[0]
    task = models.task.ClusterTask(cluster_id=c.id,
                                   task_type=models.task.TASK_TYPE_FIX_MIGRATE)
    for node in masters:
        task.add_step('fix_migrate', host=node.host, port=node.port)
    db.session.add(task)


@bp.route('/steps')
def get_task_steps():
    t = models.task.get_task_by_id(int(request.args['id']))
    if t is None:
        return abort(404)
    return json_response([{
        'id': step.id,
        'command': step.command,
        'args': step.args,
        'status': 'completed' if step.completed else (
            'running' if step.running else 'pending'),
        'start_time': f_strftime(step.start_time),
        'completion': f_strftime(step.completion),
        'exec_error': step.exec_error,
    } for step in t.all_steps])
