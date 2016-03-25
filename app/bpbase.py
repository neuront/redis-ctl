import flask


class Blueprint(flask.Blueprint):
    def __init__(self, *args, **kwargs):
        flask.Blueprint.__init__(self, *args, **kwargs)
        self.app = None

    def register(self, app, *args, **kwargs):
        self.app = app
        flask.Blueprint.register(self, app, *args, **kwargs)

    def route_post(self, url_pattern):
        return self.route(url_pattern, methods=['POST'])
