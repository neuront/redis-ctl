import handlers.base
import models.base
from models.task import TaskLock


def main():
    app = handlers.base.app
    with app.app_context():
        for lock in models.base.db.session.query(TaskLock).all():
            lock.step_id = None
            models.base.db.session.add(lock)
        models.base.db.session.commit()

if __name__ == '__main__':
    main()
