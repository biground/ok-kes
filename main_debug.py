from src.app import KesApp
from src.config import config

if __name__ == '__main__':
    config['debug'] = True
    app = KesApp(config)
    app.start()
