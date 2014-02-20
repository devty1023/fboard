import os
import datetime
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL','sqlite:///' + os.path.join(_basedir, 'app.db'))

#CELERY_BROKER_URL = 'redis://' + os.path.join(_basedir, 'broker.db')
CELERY_BROKER_URL = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
CELERYBEAT_SCHEDULE = {
    'load-posts-every-180-seconds': {
        'task': 'fboard.sync',
        'schedule': datetime.timedelta(seconds=180),
    },
}
CELERY_TIMEZONE = 'UTC'

APP_ID='1461498947403597'
APP_SECRET='ec6696790b51688a8058ab4cd7dbb0d4'
GROUP_ID='174499879257223'

SYNC_START = '1293667200' ## DEC 29 2010
SECRET = 'devty1023'

ENV = "PROD"
