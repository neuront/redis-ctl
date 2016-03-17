import os
import logging
import tempfile
from werkzeug.utils import import_string

APP_CLASS = os.getenv('APP_CLASS', 'app.RedisCtl')

OAUTH2_CLIENT_ID = os.getenv('OAUTH2_CLIENT_ID', '')
OAUTH2_CLIENT_SECRET = os.getenv('OAUTH2_CLIENT_SECRET', '')
OAUTH2_BASE_URL = os.getenv('OAUTH2_BASE_URL', 'http://sso.ricebook.net/oauth/api/')
OAUTH2_AUTHORIZE_URL = os.getenv('OAUTH2_AUTHORIZE_URL', 'http://sso.ricebook.net/oauth/authorize')
OAUTH2_ACCESS_TOKEN_URL = os.getenv('OAUTH2_ACCESS_TOKEN_URL', 'http://sso.ricebook.net/oauth/token')

SERVER_PORT = int(os.getenv('SERVER_PORT', 8000))

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
MYSQL_USERNAME = os.getenv('MYSQL_USERNAME', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'redisctl')

LOG_LEVEL = getattr(logging, os.getenv('LOG_LEVEL', 'info').upper())
LOG_FILE = os.getenv('LOG_FILE', '')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(levelname)s:%(asctime)s:%(message)s')

DEBUG = int(os.getenv('DEBUG', 0))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 10))
PERMDIR = os.getenv('ERU_PERMDIR', tempfile.gettempdir())
NODE_MAX_MEM = int(os.getenv('NODE_MAX_MEM', 2048 * 1000 * 1000))
NODES_EACH_THREAD = int(os.getenv('NODES_EACH_THREAD', 10))
REDIS_CONNECT_TIMEOUT = int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
MICRO_PLAN_MEM = int(os.getenv('MICRO_PLAN_MEM', 108 * 1000 * 1000))

# ========================= #
# Thirdparty configurations #
# ========================= #

OPEN_FALCON = {
    'host_query': os.getenv('OPEN_FALCON_HOST_QUERY', ''),
    'host_write': os.getenv('OPEN_FALCON_HOST_WRITE', ''),
    'port_query': int(os.getenv('OPEN_FALCON_PORT_QUERY', 9966)),
    'port_write': int(os.getenv('OPEN_FALCON_PORT_WRITE', 8433)),
    'db': os.getenv('OPEN_FALCON_DATABASE', 'redisctlstats'),
    'interval': int(os.getenv('OPEN_FALCON_ANTICIPATED_INTERVAL', 30)),
}

ERU = {
    'URL': os.getenv('ERU_URL', ''),
    'TIMEOUT': int(os.getenv('ERU_TIMEOUT', 5000)),
    'GROUP': os.getenv('ERU_GROUP', ''),
    'NETWORK': os.getenv('ERU_NETWORK', 'net'),
}

SKYEYE = {
    'host': os.getenv('SKYEYE_HOST', ''),
    'port': int(os.getenv('SKYEYE_PORT', 80)),
    'cooldown': int(os.getenv('SKYEYE_COOLDOWN', 900)),
}

try:
    from override_config import *
except ImportError:
    pass

from app.override import App
