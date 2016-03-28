from flask import render_template, abort, request

from app.bpbase import Blueprint
import models.node

bp = Blueprint('redis', __name__, url_prefix='/redis')


@bp.before_request
def access_control():
    if not bp.app.access_ctl_user_valid():
        abort(403)


@bp.route('/panel/<host>/<int:port>')
def node_panel(host, port):
    node = models.node.get_by_host_port(host, port)
    if node is None:
        return render_template('redis/not_found.html',
                               host=host, port=port), 404
    detail = {}
    try:
        detail = bp.app.polling_result()['nodes'][
            '%s:%d' % (node.host, node.port)]
    except (IOError, ValueError, KeyError):
        pass
    return render_template(
        'redis/panel.html', node=node, detail=detail,
        max_mem_limit=bp.app.config_node_max_mem,
        stats_enabled=bp.app.stats_enabled())


@bp.route_post_json('/add', True)
def add_redis():
    models.node.create_instance(
        request.form['host'], int(request.form['port']))


@bp.route_post_json('/del', True)
def del_redis():
    models.node.delete_free_instance(
        request.form['host'], int(request.form['port']))
