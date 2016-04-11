import time
import socket
import requests

def now():
    return int(time.time())

def _escape_name(name):
    return name.replace('.', '_').replace(':', '_')

class WriteCli(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def reconnect(self):
        if self.sock is None:
            self.sock = socket.socket()
            try:
                self.sock.connect((self.host, self.port))
            except IOError:
                self.sock.close()
                self.sock = None
                raise

    def write(self, name, value, timestamp):
        try:
            self.sock.send('%s %d %d\n' % (name, value, timestamp))
        except IOError:
            self.sock.close()
            self.sock = None
            raise

class Client(object):
    def __init__(self, write_host, write_port, query_host, query_port):
        self.write_cli = WriteCli(write_host, write_port)
        self.query_url ='http://%s:%s/render' % (query_host, query_port)

    def format_name(self, name, field):
        return 'redis.%s.%s' % (name, field)

    def write_points(self, name, fields):
        self.write_cli.reconnect()
        t = now()
        name = _escape_name(name)
        for f, v in fields.iteritems():
            self.write_cli.write(self.format_name(name, f), v, t)

    def query_field(self, name, field, aggf, span, end, interval):
        name = _escape_name(name)
        rsp = requests.post(self.query_url, data={
            'target': self.format_name(name, field),
            'format': 'json',
            'from': str(-span) + 's',
        })
        pts = rsp.json()[0]['datapoints']
        return [(p[1], p[0]) for p in pts if p[0] is not None]

    def query(self, name, fields, span, end, interval):
        result = {}
        for f, a in fields.iteritems():
            result[f] = self.query_field(name, f, a, span, end, interval)
        return result
