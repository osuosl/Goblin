from celery.task import task
import memcache
from time import sleep
from celery.log import logging
from psuproperties import Property
from psusys import PSUSys


def copy_email_task_null(login):
	prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
	log = logging.getLogger()
	memcache_url = prop.getProperty('memcache.url')
	mc = memcache.Client([memcache_url], debug=0)

	timer = 90;
	key = 'email_copy_progress.' + login

	while (timer <= 100):
		mc.set(key, timer)
		log.info('tasks.copy_email_task(), setting key: ' + key + ' to value: ' + str(timer) + " on: " + memcache_url)
		timer = timer + 1
		sleep(1)
		
	return(True)

@task
def copy_email_task(login):
	prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
	log = logging.getLogger()
	memcache_url = prop.getProperty('memcache.url')
	mc = memcache.Client([memcache_url], debug=0)
	psu_sys = PSUSys()

	log.info("copy_email_task(): processing user: " + login)
	key = 'email_copy_progress.' + login

	# Check for LDAP mail forwarding already (double checking), if
	# already opt'd-in, then immediately return and mark as complete.
	
	if (psu_sys.opt_in_already(login)):
		mc.set(key, 100)
		return(True)
	else:
		mc.set(key, 40)
	
	# Synchronize email to Google (and wait)
	psu_sys.sync_email(login)
	mc.set(key, 50)

	# Final email sync
	psu_sys.sync_email(login)
	mc.set(key, 60)
	
	# Send conversion info email to users PSU account
	psu_sys.send_conversion_email_psu(login)
	mc.set(key, 70)

	# Switch routing of email to flow to Google
	
	psu_sys.route_to_google(login)
	mc.set(key, 80)
	
	# Send conversion info email to users Google account
	psu_sys.send_conversion_email_google(login)
	mc.set(key, 90)

	# Enable Google email for the user

	psu_sys.enable_gmail_null(login)	
	mc.set(key, 100)

	return(True)
	