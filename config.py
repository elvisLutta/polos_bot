import os
from keys import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER, SEC_KEY, SITE_ADMIN
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or SEC_KEY
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    POLOS_MAIL_SUBJECT_PREFIX = '[POLOS]'
    POLOS_MAIL_SENDER = 'Polos Admin <polos@example.com>'
    SITE_ADMIN = os.environ.get('SITE_ADMIN') or SITE_ADMIN

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
    # 'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or\
        'postgresql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + \
        ':' + str(DB_PORT) + '/' + DB_NAME


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or\
        'postgresql://' + DB_USER + ':' + DB_PASS + '@' + DB_HOST + \
        ':' + str(DB_PORT) + '/' + DB_NAME



config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
