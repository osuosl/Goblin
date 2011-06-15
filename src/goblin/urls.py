from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'goblin.views.home', name='home'),
    # url(r'^goblin/', include('goblin.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    (r'^opt-in/media(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/dennis/workspace/xi/media'}),
	(r'^opt-in/js(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/dennis/workspace/xi/media/js'}),
	(r'^opt-in/status/js(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/dennis/workspace/xi/media/js'}),
	(r'^opt-in/images(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/dennis/workspace/xi/media/images'}),
	(r'^opt-in/status/images(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/home/dennis/workspace/xi/media/images'}),
	(r'^opt-in/copy_progress', 'goblin.ghoul.views.copy_progress'),
	(r'^opt-in/status', 'goblin.ghoul.views.status'),
	(r'^opt-in/confirm', 'goblin.ghoul.views.confirm'),
	(r'^opt-in/', 'goblin.ghoul.views.select'),

)
