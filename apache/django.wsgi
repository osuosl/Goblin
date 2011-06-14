import os
import sys

for path in ['/vol/goblin/src', '/vol/goblin/src/goblin']:
	if path not in sys.path:
		sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'goblin.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
