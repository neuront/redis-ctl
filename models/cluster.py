import logging
from datetime import datetime
from werkzeug.utils import cached_property

from base import db, Base, DB_STRING_TYPE


class Cluster(Base):
    __tablename__ = 'cluster'

    description = db.Column(DB_STRING_TYPE)
    creation = db.Column(db.DateTime, default=datetime.now, nullable=False)
    nodes = db.relationship('RedisNode', backref='assignee')
    proxies = db.relationship('Proxy', backref='cluster')

    @cached_property
    def current_task(self):
        from task import TaskLock
        lock = db.session.query(TaskLock).filter(
            TaskLock.cluster_id == self.id).first()
        return None if lock is None else lock.task

    def get_tasks(self, skip=0, limit=5):
        from task import ClusterTask
        return db.session.query(ClusterTask).filter(
            ClusterTask.cluster_id == self.id).order_by(
                ClusterTask.id.desc()).offset(skip).limit(limit).all()

    def get_or_create_balance_plan(self):
        from cluster_plan import ClusterBalancePlan
        p = db.session.query(ClusterBalancePlan).filter(
            ClusterBalancePlan.cluster_id == self.id).first()
        if p is None:
            p = ClusterBalancePlan(cluster_id=self.id)
            p.balance_plan = {
                'pod': None,
                'entrypoint': None,
                'slaves': [],
            }
            p.save()
        return p

    @cached_property
    def balance_plan(self):
        from cluster_plan import ClusterBalancePlan
        return ClusterBalancePlan.query.filter_by(cluster_id=self.id).first()

    def del_balance_plan(self):
        from cluster_plan import ClusterBalancePlan
        db.session.query(ClusterBalancePlan).filter(
            ClusterBalancePlan.cluster_id == self.id).delete()


def get_by_id(cluster_id):
    return db.session.query(Cluster).filter(Cluster.id == cluster_id).first()


def list_all():
    return db.session.query(Cluster).all()


def create_cluster(description):
    c = Cluster(description=description)
    db.session.add(c)
    db.session.flush()
    return c


def remove_empty_cluster(cluster_id):
    c = get_by_id(cluster_id)
    if len(c.nodes) == 0:
        logging.info('Remove cluster %d', cluster_id)
        c.proxies = []
        db.session.add(c)
        db.session.flush()
        db.session.delete(c)
