from flask import render_template, abort

from app.bpbase import Blueprint
from thirdparty import eru_utils
import models.cluster

bp = Blueprint('cluster', __name__, url_prefix='/cluster')


@bp.route('/panel/<int:cluster_id>')
def cluster_panel(cluster_id):
    c = models.cluster.get_by_id(cluster_id)
    if c is None or len(c.nodes) == 0:
        return abort(404)
    all_details = bp.app.polling_result()
    node_details = all_details['nodes']
    nodes = []
    for n in c.nodes:
        detail = node_details.get('%s:%d' % (n.host, n.port))
        if detail is None:
            nodes.append({'host': n.host, 'port': n.port, 'stat': False})
        else:
            nodes.append(detail)
    proxy_details = all_details['proxies']
    for p in c.proxies:
        p.details = proxy_details.get('%s:%d' % (p.host, p.port), {})
    return render_template('cluster/panel.html', cluster=c, nodes=nodes,
                           eru_client=eru_utils.eru_client, plan_max_slaves=3,
                           stats_enabled=bp.app.stats_enabled())
