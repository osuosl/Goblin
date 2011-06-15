import os
import sys

for path in ['/vol/goblin/src', '/vol/goblin/src/goblin', '/vol/d2l/ragve/lib/python', '/vol/google-imap']:
	if path not in sys.path:
		sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'goblin.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
