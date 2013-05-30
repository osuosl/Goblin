import os
import sys

for path in [ '/var/www/goblin/shared/env/bin','/home/vagrant/goblin/etc']:
	if path not in sys.path:
		sys.path.append(path)

ACTIVATE = os.path.join(PROJECT_PATH, 'pythonenv/bin/activate_this.py')

sys.path.insert(0, PROJECT_PATH)
 
execfile( ACTIVATE, dict(__file__=ACTIVATE) )

os.environ['DJANGO_SETTINGS_MODULE'] = 'goblin.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
