# Create your views here.
#from django.contrib.flatpages.models import FlatPage
from django.shortcuts import render_to_response
#from django.http import HttpResponseRedirect
from django.http import HttpResponse
#from django.http import HttpRequest
from django.template import RequestContext
#from django.core.cache import cache
from tasks import copy_email_task
#from celery.task import task
#from psuproperties import Property
from psusys import PSUSys
import logging

log = logging.getLogger('ghoul.views')

def select(request):
	#query = request.GET['q']
	login = request.POST.get('login', '')
	login = request.META['REMOTE_USER'] 
	if not login:
		login = 'weekse'

	log.info('views.select() META: ' + str(request.META) )
	log.info('views.select() called with login: ' + login)
	
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

	log.info('views.copy_progress() called with login: ' + login)
	
	if not login:
		login = 'weekse'

	log.info('views.copy_progress() called with login: ' + login)

	return HttpResponse(psu_sys.copy_progress(login))


def status(request):
	#query = request.GET['q']
	login = request.POST.get('login', '')
	login = login.encode('latin-1')

	log.info('views.status() called with user: ' + login)
	log.info('views.status() META: ' + str(request.META) )

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
	#query = request.GET['q']
	login = request.GET.get('login', '')
	if not login:
		login = 'dennis'

	log.info('views.confirm() called with user: ' + login)
	log.info('views.confirm() META: ' + str(request.META) )

	long_folders = ['Advertisements/Electronics/TimeDomainReflectometry'] 
	large_emails = ["Platinum Group Metal Compounds and Salts", 'Filter design', 'Webdav Issues']
	
	return render_to_response('ghoul/confirm.html', 
		{ 'login': login,
		  'long_folders': long_folders,
		  'large_emails': large_emails,
		  },
		context_instance=RequestContext(request))

		
	
