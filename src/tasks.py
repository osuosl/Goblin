from celery.task import task
import memcache
from time import sleep

@task
def copy_email_task(login):
	mc = memcache.Client(['127.0.0.1:11211'], debug=0)
	timer = 70;
	
	#key = 'email_copy_progress.' + login
	key = 'email_copy_progress.' + 'dennis'
	while (timer <= 100):
		mc.set(key, timer)
		timer = timer + 1
		sleep(1)
		
	return(True)
	