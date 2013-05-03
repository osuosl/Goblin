import os
import sys

for path in [ '/home/vagrant/goblin/etc', '/vol/goblin/src', '/vol/goblin/src/goblin', '/vol/ragve/lib/python', '/vol/google-imap', '/vol/crypt', '/vol/goblin/etc', '/usr/local/lib/python2.6/dist-packages' ]:
	if path not in sys.path:
		sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'goblin.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
