import gevent
import gevent.monkey

gevent.monkey.patch_all()

import config
from daemonutils import stats_models as _
from app.api import RedisMuninApp


def run(interval, app):
    from daemonutils.node_polling import NodeStatCollector
    from daemonutils.cluster_task import TaskPoller

    daemons = [
        TaskPoller(app, interval),
        NodeStatCollector(app, interval),
    ]
    for d in daemons:
        d.start()
    for d in daemons:
        d.join()


def main():
    app = RedisMuninApp()
    app.init_clients(config)
    run(config.POLL_INTERVAL, app)

if __name__ == '__main__':
    main()
