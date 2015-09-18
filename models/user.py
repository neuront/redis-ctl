import uuid
from datetime import datetime, timedelta
from werkzeug.utils import cached_property
from sqlalchemy.exc import IntegrityError

from base import db, Base

PRIV_USER = 1
PRIV_ADMIN = PRIV_USER << 1


class User(Base):
    __tablename__ = 'user'

    username = db.Column(db.String(64), unique=True, nullable=False)
    username_lower = db.Column(db.String(64), unique=True, nullable=False)
    openid = db.Column(db.String(64), unique=True, nullable=False)
    nickname = db.Column(db.Unicode(64), index=True, nullable=False)
    avatar = db.Column(db.String(128), nullable=False, default=lambda: '')
    description = db.Column(db.UnicodeText, nullable=False, default=lambda: '')
    priv_flags = db.Column(db.Integer, nullable=False, default=lambda: 0)

    def save(self):
        self.username_lower = self.username.lower()
        db.session.add(self)
        db.session.flush()

    @cached_property
    def active(self):
        return self.priv_flags & PRIV_USER != 0

    @cached_property
    def is_adv(self):
        return self.priv_flags & PRIV_ADMIN != 0

    @cached_property
    def is_admin(self):
        return self.priv_flags & PRIV_ADMIN != 0


def robot():
    u = get_by_username('_')
    if u is None:
        try:
            u = User(username='_', openid='', nickname='Robot',
                     description='I am the robot')
            u.save()
            db.session.commit()
        except IntegrityError:
            u = get_by_username('_')
    return u


class UserAuthKey(db.Model):
    __tablename__ = 'user_auth_key'

    key = db.Column('key', db.CHAR(36), primary_key=True)
    user_id = db.Column('user_id', db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(User)
    expiration = db.Column('expiration', db.DateTime, nullable=False)

    @staticmethod
    def gen_for(user):
        key = UserAuthKey(user=user, key=str(uuid.uuid4()),
                          expiration=datetime.now() + timedelta(days=14))
        db.session.add(key)
        db.session.commit()
        return key


def _clear_timeout():
    for k in db.session.query(UserAuthKey).filter(
            UserAuthKey.expiration < datetime.now()).all():
        db.session.delete(k)
    db.session.flush()
    db.session.commit()


def get_by_id(uid):
    return None if uid is None else db.session.query(User).filter(
        User.id == uid).first()


def get_by_username(username):
    return db.session.query(User).filter(
        User.username_lower == username.lower()).first()


def get_by_openid(openid):
    return db.session.query(User).filter(User.openid == openid).first()


def invalidate_auth_key(auth_key):
    k = db.session.query(UserAuthKey).filter(
        UserAuthKey.key == auth_key).first()
    if k is not None:
        db.session.delete(k)


def invalidate_auth_keys_of_user(user):
    for k in db.session.query(UserAuthKey).filter(
            UserAuthKey.user == user).all():
        db.session.delete(k)


def get_by_auth_key(auth_key):
    _clear_timeout()
    k = db.session.query(UserAuthKey).filter(
        UserAuthKey.key == auth_key).first()
    return None if k is None else k.user


def list():
    return db.session.query(User).order_by(db.desc(User.id)).all()
