from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from tasks import copy_email_task
from psusys import PSUSys
import logging

log = logging.getLogger('ghoul.views')

def select(request):
	if 'REMOTE_USER' in request.META:
		login = request.META['REMOTE_USER'] 
		log.info('views.select() META: ' + str(request.META) )
	else:
		login = 'dennis'
		log.info('views.select() login not found, defaulting to : ' + login)

	log.info('views.select() using login: ' + login)
	
	psu_sys = PSUSys()
	large_emails = psu_sys.large_emails(login)
			
	return render_to_response('ghoul/select.html', 
		{ 'login': login,
		  'large_emails': large_emails,
		  },
		context_instance=RequestContext(request),
	)
	
def copy_progress(request):
	psu_sys = PSUSys()
	login = request.GET.get('login', '')
	login = login.encode('latin-1')
	if not login:
		log.info('views.copy_progress() login name not found')
		login = 'dennis'

	log.info('views.copy_progress() using login: ' + login)
	return HttpResponse(psu_sys.copy_progress(login))


def status(request):
	if 'REMOTE_USER' in request.META:
		login = request.META['REMOTE_USER'] 
		log.info('views.status() login found in META: ' + login )
	else:
		if 'login' in request.POST:
			login = request.POST['login']
			log.info('views.status() login found in POST: ' + login )
		else: 
			login = 'dennis'
			log.info('views.status() login not found, defaulting to : ' + login)		
			
	log.info('views.status() META: ' + str(request.META) )
	login = login.encode('latin-1')
	
	
	#key = 'email_copy_progress.' + login
	#if ( cache.get(key) == None ):
	#	log.info('views.status() cache.get(key): None')
		
		#copy_email_task.delay(login)
	log.info('views.status() called celery task')
	copy_email_task.apply_async(args=[login], queue='optin')
		
	return render_to_response('ghoul/status.html', 
		{ 'login': login, },
		context_instance=RequestContext(request))
	
def confirm(request):
	if 'REMOTE_USER' in request.META:
		login = request.META['REMOTE_USER'] 
		log.info('views.confirm() login found in META: ' + login )
	else:
		if 'login' in request.POST:
			login = request.POST['login']
			log.info('views.confirm() login found in POST: ' + login )
		else: 
			login = 'dennis'
			log.info('views.confirm() login not found, defaulting to : ' + login)		

	psu_sys = PSUSys()
	large_emails = psu_sys.large_emails(login)
	
	return render_to_response('ghoul/confirm.html', 
		{ 'login': login,
		  'large_emails': large_emails,
		  },
		context_instance=RequestContext(request))

		
	
