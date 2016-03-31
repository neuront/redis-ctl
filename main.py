import config
import handlers


def main():
    app = handlers.base.app
    app.write_polling_targets()
    app.run(host='127.0.0.1' if app.debug else '0.0.0.0',
            port=config.SERVER_PORT)

if __name__ == '__main__':
    main()
