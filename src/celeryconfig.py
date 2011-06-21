#BROKER_HOST = 'sync.oit.pdx.edu'
BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'optin'
BROKER_PASSWORD = 'CbXVtHJHFmwgE'
BROKER_VHOST = 'optin'
CELERY_RESULT_BACKEND = "amqp"
CELERY_IMPORTS = ("tasks", )
CELERYD_LOG_FILE = '/vol/goblin/var/celery.log'
CELERYD_LOG_LEVEL = 'INFO'
CELERY_ROUTES = {"tasks.copy_email_task": {"queue": "optin"}}


