from werkzeug.utils import cached_property
from eruhttp import EruException

from base import db, Base
from cluster import Cluster


class RedisNode(Base):
    __tablename__ = 'redis_node'

    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    eru_container_id = db.Column(db.String(64), index=True)
    assignee_id = db.Column(db.ForeignKey(Cluster.id), index=True)
    suppress_alert = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (db.Index('address', 'host', 'port', unique=True),)

    def free(self):
        return self.assignee_id is None

    @cached_property
    def eru_deployed(self):
        return self.eru_container_id is not None

    @cached_property
    def eru_info(self):
        from flask import g
        if g.container_client is None or not self.eru_deployed:
            return None
        return g.container_client.get_container(self.eru_container_id)


def get_by_host_port(host, port):
    return db.session.query(RedisNode).filter(
        RedisNode.host == host, RedisNode.port == port).first()


def list_eru_nodes(offset, limit):
    return db.session.query(RedisNode).filter(
        RedisNode.eru_container_id != None).order_by(
            RedisNode.id.desc()).offset(offset).limit(limit).all()


def list_all_nodes():
    return db.session.query(RedisNode).all()


def create_instance(host, port):
    node = RedisNode(host=host, port=port)
    db.session.add(node)
    db.session.flush()
    return node


def create_eru_instance(host, port, eru_container_id):
    node = RedisNode(host=host, port=port, eru_container_id=eru_container_id)
    db.session.add(node)
    db.session.flush()
    return node


def delete_eru_instance(eru_container_id):
    i = db.session.query(RedisNode).filter(
        RedisNode.eru_container_id == eru_container_id).first()
    if i is None or i.assignee_id is not None:
        raise ValueError('node not free')
    db.session.delete(i)


def get_eru_by_container_id(eru_container_id):
    return db.session.query(RedisNode).filter(
        RedisNode.eru_container_id == eru_container_id).first()


def delete_free_instance(host, port):
    node = db.session.query(RedisNode).filter(
        RedisNode.host == host,
        RedisNode.port == port,
        RedisNode.assignee_id == None).with_for_update().first()
    if node is not None:
        db.session.delete(node)
