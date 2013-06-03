import os, sys

# get root of project
path =  os.path.dirname(os.path.realpath(__file__))
path = '/var/www/goblin/shared/env'

# activate virtual environment
activate_this = '%s/bin/activate_this.py' % path
execfile(activate_this, dict(__file__=activate_this))


sys.path.insert(0, '/var/www/goblin/current')
os.environ['DJANGO_SETTINGS_MODULE'] = 'goblin.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
