from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
from tasks import copy_email_task
from psusys import PSUSys
import logging
#from celery.task import Task
log = logging.getLogger('ghoul.views')

def select(request):
	if 'REMOTE_USER' in request.META:
		login = request.META['REMOTE_USER'] 
		request.session['login'] = login
		log.info('views.select() found user in META: ' + login )
	else:
		if 'login' in request.POST:
			login = request.POST['login']
			request.session['login'] = login
			log.info('views.select() login found in POST: ' + login )
		else: 
			if 'login' in request.session:
				login = request.session['login']
				log.info('views.select() login found in session: ' + login )
			else:
				login = 'dennis'
				log.info('views.select() login not found, defaulting to : ' + login)		

	log.info('views.select() using login: ' + login)
	
	psu_sys = PSUSys()
	psu_sys.set_user(login, request.META)

	# Go to the confirmation page if the user has already opt'd-in
	
	# Go to informational page for folks who are not yet allowed-in
	if not psu_sys.is_allowed(login):
		return render_to_response('ghoul/closed.html', { 'login': login },
								context_instance=RequestContext(request),)
		
		
	if psu_sys.opt_in_already(login):
		return render_to_response('ghoul/confirm.html', { 'login': login },
								context_instance=RequestContext(request),)
	
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
			if 'login' in request.session:
				login = request.session['login']
				log.info('views.status() login found in session: ' + login )
			else: 
				login = 'dennis'
				log.info('views.status() login not found, defaulting to : ' + login)		
			
	log.info('views.status() META: ' + str(request.META) )
	login = login.encode('latin-1')
	
	
	#key = 'email_copy_progress.' + login
	#if ( cache.get(key) == None ):
	#	log.info('views.status() cache.get(key): None')

	psu_sys = PSUSys()
	if psu_sys.is_processing(login):
		pass
	else:
		log.info('views.status() called celery task for user: ' + login)
		copy_email_task.apply_async(args=[login], queue='optin')
		
	return render_to_response('ghoul/status.html', 
		{ 'login': login, },
		context_instance=RequestContext(request))
	
def confirm(request):
	psu_sys = PSUSys()
	if 'REMOTE_USER' in request.META:
		login = request.META['REMOTE_USER'] 
		log.info('views.confirm() login found in META: ' + login )
	else:
		if 'login' in request.POST:
			login = request.POST['login']
			log.info('views.confirm() login found in POST: ' + login )
		else: 
			if 'login' in request.session:
				login = request.session['login']
				log.info('views.status() login found in session: ' + login )
			else:
				login = psu_sys.get_user(request.META)
				log.info('views.confirm() login not found, defaulting to : ' + login)		
	
	#log.info('views.confirm(), META = ' + str(request.META))
	
	large_emails = psu_sys.large_emails(login)
	
	return render_to_response('ghoul/confirm.html', 
		{ 'login': login,
		  'large_emails': large_emails,
		  },
		context_instance=RequestContext(request))

		
	
