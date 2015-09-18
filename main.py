import config
import sys
import signal


def main():
    app = config.App(config)
    app.register_blueprints()
    app.write_polling_targets()
    app.run(host='127.0.0.1' if app.debug else '0.0.0.0',
            port=config.SERVER_PORT)


def exit_program(*args, **kwargs):
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGHUP, exit_program)
    main()
