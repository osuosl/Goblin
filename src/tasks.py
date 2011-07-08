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
	psu_sys = PSUSys()
	return(psu_sys.copy_email_task(login))


	