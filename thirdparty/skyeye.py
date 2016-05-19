import logging
import requests
import json


class SkyEyeClient(object):
    def __init__(self, host, port):
        self.url = 'http://%s:%d/api/alarms/submit' % (host, port)

    def __str__(self):
        return 'SkyEye <%s>' % self.url

    def send_alarm(self, message, trace):
        try:
            requests.post(self.url, json.dumps([{
                'source': 'redisctl',
                'severity': 'A',
                'status': 'Error',
                'metric': 'redis.connected',
                'target': 'redis',
                'tags': {'type': 'redis'},
                'msg': message,
            }]))
        except IOError as e:
            logging.exception(e)
