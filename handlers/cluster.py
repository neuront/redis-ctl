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
