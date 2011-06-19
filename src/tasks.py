from celery.task import task
import memcache
from time import sleep
from celery.log import logging

@task
def copy_email_task(login):
	#mc = memcache.Client(['imapsync-mc.oit.pdx.edu:11211'], debug=0)
	mc = memcache.Client(['localhost:11211'], debug=0)
	timer = 90;
	logging.info('test')
	log = logging.getLogger()
	#key = 'email_copy_progress.' + login
	key = 'email_copy_progress.' + login
	while (timer <= 100):
		mc.set(key, timer)
		log.info('tasks.copy_email_task(), login: ' + login + ', timer: ' + str(timer))
		timer = timer + 1
		sleep(1)
		
	return(True)
	