import base
import models.node
import models.proxy
import models.task
from models.base import db


@base.post_async('/nodes/add')
def add_node(request):
    models.node.create_instance(
        request.form['host'], int(request.form['port']))


@base.post_async('/nodes/del')
def del_node(request):
    models.node.delete_free_instance(
        request.form['host'], int(request.form['port']))
