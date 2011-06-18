# Create your views here.
#from django.contrib.flatpages.models import FlatPage
from django.shortcuts import render_to_response
#from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.cache import cache
from tasks import copy_email_task
from celery.task import task
#from psuproperties import Property
from psusys import PSUSys

def select(request):
	#query = request.GET['q']
	login = request.GET.get('login', '')
	if not login:
		login = 'dennis'
	
	psu_sys = PSUSys()
	large_emails = psu_sys.large_emails(login)
			
	return render_to_response('ghoul/select.html', 
		{ 'login': login,
		  #'long_folders': long_folders,
		  'large_emails': large_emails,
		  })
	
def copy_progress(request):
	import simplejson
	import memcache	
	mc = memcache.Client(['localhost:11211'], debug=0)

	#cache_key = "copy_progress_%s" % (request.GET['login', 'default'])
	key = 'email_copy_progress.' + 'dennis'
	cached_data = mc.get(key)
	if (cached_data == None):
		cached_data = 0
	#data = simplejson.dumps(cached_data)
	data = simplejson.dumps(cached_data)
	#data = [42]
	return HttpResponse(data)
	#return HttpResponse(simplejson.dumps(27))


def status(request):
	#query = request.GET['q']
	login = request.GET.get('login', '')
	if not login:
		login = 'dennis'
	
	key = 'email_copy_progress.' + login
	if ( cache.get(key) == None ):
		copy_email_task.delay(login)
		
	return render_to_response('ghoul/status.html', 
		{ 'login': login,
				})
def confirm(request):
	#query = request.GET['q']
	login = request.GET.get('login', '')
	if not login:
		login = 'dennis'

	long_folders = ['Advertisements/Electronics/TimeDomainReflectometry'] 
	large_emails = ["Platinum Group Metal Compounds and Salts", 'Filter design', 'Webdav Issues']
	
	return render_to_response('ghoul/confirm.html', 
		{ 'login': login,
		  'long_folders': long_folders,
		  'large_emails': large_emails,
		  })
		
	
