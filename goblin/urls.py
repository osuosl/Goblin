from django.conf.urls.defaults import patterns, include, url
from goblin.ghoul.forms import FORMS
from goblin.ghoul.views import (MigrationWizard, show_migrate, show_transition,
                                show_confirm_trans, show_forward_notice,
                                show_confirm)

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    (r'^status/js(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/var/www/goblin/doc/js'}),
    (r'^status/images(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/var/www/goblin/doc/images'}),
    (r'^copy_progress', 'goblin.ghoul.views.copy_progress'),
    (r'^status', 'goblin.ghoul.views.status'),
    (r'^confirm', 'goblin.ghoul.views.confirm'),
    (r'^select', 'goblin.ghoul.views.select'),
    (r'^progress', 'goblin.ghoul.views.progress'),
    (r'^', MigrationWizard.as_view(FORMS,
           condition_dict={'migrate': show_migrate,
                           'transition': show_transition,
                           'confirm_trans': show_confirm_trans,
                           'forward_notice': show_forward_notice,
                           'confirm': show_confirm,})),
)
