from flask import render_template

from app.bpbase import Blueprint
import models.node

bp = Blueprint('redis', __name__, url_prefix='/redis')


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
