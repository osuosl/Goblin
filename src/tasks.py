from celery.task import task
import memcache
from time import sleep
from celery.log import logging
from psuproperties import Property
from psusys import PSUSys

@task
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
	log = logging.getLogger()
	log.info('copy_email_task(): running copy_email_task(' + login + ')')
	psu_sys = PSUSys()
	result = psu_sys.copy_email_task(login) 
	log.info('copy_email_task(): finished running copy_email_task(' + login + ')')
	return(result)

@task
def recover_copy_email_task(login):
	log = logging.getLogger()
	log.info('copy_email_task(): running recover_copy_email_task(' + login + ')')
	psu_sys = PSUSys()
	result = psu_sys.recover_copy_email_task(login) 
	log.info('copy_email_task(): finished running recover_copy_email_task(' + login + ')')
	return(result)

@task
def sync_email_task(login):
	log = logging.getLogger()
	log.info('sync_email_task(): running sync_email_task(' + login + ')')
	psu_sys = PSUSys()
	result = psu_sys.sync_email(login)
	log.info('sync_email_task(): finished running sync_email_task(' + login + ')')
	return(result)

@task
def sync_email_delete2_task(login):
	log = logging.getLogger()
	log.info('sync_email_delete2_task(): running sync_email_delete2_task(' + login + ')')
	psu_sys = PSUSys()
	result = psu_sys.sync_email_delete2(login)
	log.info('sync_email_task(): finished running sync_email_delete2_task(' + login + ')')
	return(result)
		
