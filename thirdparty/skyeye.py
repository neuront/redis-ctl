import logging
import requests
import json
from thirdparty.alarm import Timed


class SkyEyeClient(Timed):
    def __init__(self, host, port, cooldown):
        Timed.__init__(self, cooldown)
        self.url = 'http://%s:%d/api/alarms/submit' % (host, port)

    def __str__(self):
        return 'SkyEye <%s>' % self.url

    def do_send_alarm(self, endpoint, message, exception, **kwargs):
        logging.error('Send alarm for %s:%d because %s',
                      endpoint.host, endpoint.port, message)
        try:
            requests.post(self.url, json.dumps([{
                'source': 'redisctl',
                'severity': 'A',
                'status': 'Error',
                'metric': 'redis.connected',
                'target': 'redis-%s:%s' % (endpoint.host, endpoint.port),
                'tags': {'type': 'redis'},
                'msg': message,
            }]))
        except IOError as e:
            logging.exception(e)
