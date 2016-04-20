import logging
import time
import threading
from redistrib.clusternode import Talker
from sqlalchemy.exc import IntegrityError

import base
import file_ipc
import models.audit
import models.node
import models.proxy
import models.cluster


def _set_proxy_remote(proxy_addr, proxy_port, redis_host, redis_port):
    def set_remotes():
        time.sleep(1)
        t = Talker(proxy_addr, proxy_port)
        try:
            t.talk('SETREMOTES', redis_host, redis_port)
        finally:
            t.close()
    threading.Thread(target=set_remotes).start()
