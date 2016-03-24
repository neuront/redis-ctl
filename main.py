import config
import handlers
import file_ipc


def main():
    app = handlers.base.app
    file_ipc.write_nodes_proxies_from_db()
    app.run(host='127.0.0.1' if app.debug else '0.0.0.0',
            port=config.SERVER_PORT)

if __name__ == '__main__':
    main()
