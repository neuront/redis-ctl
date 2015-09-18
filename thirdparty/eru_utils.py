import logging
from functools import wraps
from retrying import retry
from eruhttp import EruClient, EruException

from app.utils import datetime_str_to_timestamp
from containerize import Base, ContainerizeExceptionBase
import models.pod_network


def exception_adapt(f):
    @wraps(f)
    def g(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except EruException as e:
            raise ContainerizeExceptionBase(e)
    return g


class DockerClient(Base):
    def __init__(self, config):
        Base.__init__(self, config)
        self.client = EruClient(config.ERU['URL'])
        self.group = config.ERU['GROUP']
        self.network = config.ERU['NETWORK']

    def __str__(self):
        return 'Eru Services <%s>' % self.client.url

    def cpu_slice(self):
        return 10

    @retry(stop_max_attempt_number=64, wait_fixed=500)
    def poll_task_for_container_id(self, task_id):
        r = self.client.get_task(task_id)
        if r['result'] != 1:
            raise ValueError('task not finished')
        try:
            return r['props']['container_ids'][0]
        except LookupError:
            logging.error('Eru returns invalid container info task<%d>: %s',
                          task_id, r)
            return None

    def _list_images(self, what, offset, limit):
        return [{
            'name': i['sha'],
            'description': '',
            'creation': datetime_str_to_timestamp(i['created']),
        } for i in self.client.list_app_versions(
            what, offset, limit)['versions']]

    def list_redis_images(self, offset, limit):
        return self._list_images('redis', offset, limit)

    def lastest_image(self, what):
        try:
            return self.client.list_app_versions(what)['versions'][0]['sha']
        except LookupError:
            raise ValueError('eru fail to give version SHA of ' + what)

    @exception_adapt
    def deploy(self, what, pod, entrypoint, ncore, host, port, args,
               image=None):
        logging.info('Deploy %s to pod=%s entry=%s cores=%d addr=%s:%d :%s:',
                     what, pod, entrypoint, ncore, host, port, args)
        network = self.client.get_network(
            models.pod_network.get_network(pod, self.network))
        if not image:
            image = self.lastest_image(what)
        r = self.client.deploy_private(
            self.group, pod, what, ncore, 1, image,
            entrypoint, 'prod', [network['id']], host_name=host, args=args)
        try:
            task_id = r['tasks'][0]
            logging.info('Task created: %s', task_id)
        except LookupError:
            raise ValueError('eru fail to create a task ' + str(r))

        cid = self.poll_task_for_container_id(task_id)
        if cid is None:
            raise ValueError('eru returns invalid container info')
        try:
            container_info = self.client.get_container(cid)
            logging.debug('Task %d container info=%s', task_id, container_info)
            addr = host = container_info['host']
            if len(container_info['networks']) != 0:
                addr = container_info['networks'][0]['address']
            created = container_info['created']
        except LookupError, e:
            raise ValueError('eru gives incorrent container info: %s missing %s'
                             % (cid, e.message))
        return {
            'version': image,
            'container_id': cid,
            'address': addr,
            'host': host,
            'created': created,
        }

    @exception_adapt
    def get_container(self, container_id):
        try:
            return self.client.get_container(container_id)
        except EruException as e:
            logging.exception(e)
            return {
                'version': '-',
                'host': '-',
                'created': 'CONTAINER NOT ALIVE',
            }

    @exception_adapt
    def rm_containers(self, container_ids):
        logging.info('Remove containers: %s', container_ids)
        try:
            self.client.remove_containers(container_ids)
        except EruException as e:
            logging.exception(e)

    @exception_adapt
    def revive_container(self, container_id):
        logging.debug('Revive container: %s', container_id)
        self.client.start_container(container_id)

    @exception_adapt
    def list_pods(self):
        return self.client.list_pods()

    @exception_adapt
    def list_pod_hosts(self, pod):
        return self.client.list_pod_hosts(pod)
