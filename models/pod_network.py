from base import db, Base
import config


class PodNetwork(Base):
    __tablename__ = 'pod_network'

    pod = db.Column(db.String(255), nullable=False, unique=True)
    network = db.Column(db.String(255), nullable=False)


def get_network(pod):
    n = PodNetwork.query.filter_by(pod=pod).first()
    return config.ERU_NETWORK if n is None else n.network
