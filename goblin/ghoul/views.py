from subprocess import PIPE, Popen

from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.contrib.formtools.wizard.views import SessionWizardView
from tasks import *
from psusys import PSUSys
import logging
from string import lower

import os

from goblin.ghoul.forms import FORMS

import celeryconfig

log = logging.getLogger('ghoul.views')

TEMPLATES = {"migrate": "ghoul/form_wizard/step1yes.html",
             "transition": "ghoul/form_wizard/step1no.html",
             "confirm_trans": "ghoul/form_wizard/step1noB.html",
             "forward_notice": "ghoul/form_wizard/step2yes.html",
             "prohibit": "ghoul/form_wizard/step2no.html",
             "mobile": "ghoul/form_wizard/step3.html",
             "confirm": "ghoul/form_wizard/step4yes.html",
             "final_confirm": "ghoul/form_wizard/step4no.html"}

def get_login(wizard):
    """
    Get user account name

    This comes from the various methods
    """

    if 'REMOTE_USER' in wizard.request.META:
        wizard.login = lower(wizard.request.META['REMOTE_USER'])
        wizard.request.session['login'] = wizard.login
    else:
        if 'login' in wizard.request.POST:
            wizard.login = lower(wizard.request.POST['login'])
            wizard.request.session['login'] = wizard.login
        else:
            if 'login' in wizard.request.session:
                wizard.login = wizard.request.session['login']

def presync_set(wizard):
    if not wizard.login:
        get_login(wizard)

    return wizard.psusys.presync_enabled(wizard.login)

def presync(wizard):
    """
    presync:
        Check ldap to see if 'login' has the googlePreSync flag set.
        If the flag is set, return true.
    """
    return presync_set(wizard)

def no_presync(wizard):
    """
    no_presync:
        Check ldap to see if 'login' has the googlePreSync flag set.
        If the flag is not set, return true.
    """
    return not presync_set(wizard)

def forward_set(wizard):
    """
    forward_set:
        Shell out to a perl script to see if the user has a forward setup
    """
    if wizard.forward is None:
        get_fwd = '/var/www/goblin/current/bin/get-cyrus-fwd.pl'
        fwd_cfg = '/var/www/goblin/current/etc/imap_fwd.cfg'
        wizard.forward = Popen(['perl', get_fwd, fwd_cfg, wizard.login],
                                stdout=PIPE).communicate()[0]

    # Now to handle the information returned
    location = wizard.psusys.prop.get('imap.host')
    location_str = "Could not connect to mail server %s, please try again." %\
                   location

    # If wizard.form is not set or the perl script returns the location
    # string, return False
    if wizard.forward in [None, location_str]:
        return False

    # If the word none is found within the output of the perl script,
    # return False
    if 'none' in wizard.forward:
        return False

    # If we are given any other response by the perl script,
    # return True
    return True

def progress(request):
    """
    Show the user the final info and a progress bar of their
    transfer status
    """
    return render_to_response('ghoul/form_wizard/step5done.html', {
        'page_title': "Migration in Progress",
    })

def missing_google_account(request):
    """
    Error page when the user does not have an account
    """
    return render_to_respons('ghoul/no_gmail_account.html', {
        'page_titile': "No google account exists",
    })


class MigrationWizard(SessionWizardView):
    """
    SessionWizardView for the ond->gmail migration
    """

    page_titles = {"migrate": {'page_title': "Are You Ready to Move Your ONID \
                                             Mailbox to Google?"},
                   "transition":  {'page_title': "Are You Ready to Transition \
                                                 Your ONID Mailbox \
                                                 to Google?"},
                   "confirm_trans": {'page_title': "Current Email Will \
                                                        Not Be Migrated"},
                   "forward_notice": {'page_title': "Notice to Reset Your \
                                                    Forward"},
                   "prohibit": {'page_title': "Prohibited Data Notice"},
                   "mobile": {'page_title': "Mobile Access Notice"},
                   "confirm": {'page_title': "Confirm"},
                   "final_confirm": {'page_title': "Final Confirm"},}

    psusys = PSUSys()

    forward = None
    login = None

    def get_context_data(self, form, **kwargs):
        context = super(MigrationWizard, self)\
                  .get_context_data(form=form, **kwargs)
        context.update(self.page_titles.get(self.steps.current))
        if self.steps.current == "forward_notice":
            context.update({"forward": self.forward})
        return context

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def done(self, form_list, **kwargs):
        """
        Step5done is the final step of the form, which is just a
        reiteration of all the pages the user just went through.
        """
        # Celery task: copy_email_task
        copy_email_task.apply_async(args=[self.login], queue='optinpresync')
        # Now that emails are sent and conversion has kicked off,
        # redirect the user to the progress page
        return HttpResponseRedirect('/progress')


def select(request):
    if 'REMOTE_USER' in request.META:
        login = lower(request.META['REMOTE_USER'])
        request.session['login'] = login
        log.info('views.select() found user in META: ' + login)
    else:
        if 'login' in request.POST:
            login = lower(request.POST['login'])
            request.session['login'] = login
            log.info('views.select() login found in POST: ' + login)
        else:
            if 'login' in request.session:
                login = request.session['login']
                log.info('views.select() login found in session: ' + login)
            else:
                login = 'dennis'
                log.info('views.select() login not found, defaulting to : ' +
                         login)

    log.info('views.select() using login: ' + login)

    psu_sys = PSUSys()
    psu_sys.set_user(login, request.META)

    # Go to informational page for folks who are not yet allowed-in
    if not psu_sys.is_allowed(login):
        status_message = "psu_sys.is_allowed is false"
        return render_to_response('ghoul/notyet.html',
                                  {'login': login,
                                   'status_message': status_message},
                                  context_instance=RequestContext(request),)
    # Go to the confirmation page if the user has already opt'd-in
    if psu_sys.opt_in_already(login):
        status_message = "you are opted-in already"
        return render_to_response('ghoul/notyet.html',
                                  {'login': login,
                                   'status_message': status_message},
                                  context_instance=RequestContext(request),)
    # Go to suspended page if site is not available
    if psu_sys.is_web_suspended(login):
        status_message = "web is suspended"
        return render_to_response('ghoul/notyet.html',
                                  {'login': login,
                                   'status_message': status_message},
                                  context_instance=RequestContext(request),)
    if psu_sys.is_processing(login):
        status_message = "we are already processing this user"
        return render_to_response('ghoul/notyet.html',
                                  {'login': login,
                                   'status_message': status_message},
                                  context_instance=RequestContext(request),)

    # So, folderbombing is a thing
    try:
        psu_sys.large_emails = psu_sys.large_emails(login)
    except:
        return render_to_response('ghoul/folderbomb.html', {'login': login},
                                  context_instance=RequestContext(request),)

    # If nothing special, begin the wizard
    if psu_sys.presync_enabled(login):
        template = 'ghoul/form_wizard/step1yes.html'
    else:
        template = 'ghoul/form_wizard/step1no.html'

    return render_to_response(template,
                              {'login': login,
                               'large_emails': psu_sys.large_emails},
                              context_instance=RequestContext(request),)


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
        log.info('views.status() login found in META: ' + login)
    else:
        if 'login' in request.POST:
            login = request.POST['login']
            log.info('views.status() login found in POST: ' + login)
        else:
            if 'login' in request.session:
                login = request.session['login']
                log.info('views.status() login found in session: ' + login)
            else:
                login = 'dennis'
                log.info('views.status() login not found, defaulting to : ' +
                         login)

    log.info('views.status() META: ' + str(request.META))
    login = login.encode('latin-1')

    #key = 'email_copy_progress.' + login
    #if ( cache.get(key) == None ):
    #    log.info('views.status() cache.get(key): None')

    psu_sys = PSUSys()
    if psu_sys.is_processing(login):
        pass
    else:
        log.info('views.status() called celery task for user: ' + login)
        copy_email_task.apply_async(args=[login], queue='optin')

    return render_to_response('ghoul/status.html',
                              {'login': login},
                              context_instance=RequestContext(request))


def confirm(request):
    psu_sys = PSUSys()
    if 'REMOTE_USER' in request.META:
        login = request.META['REMOTE_USER']
        log.info('views.confirm() login found in META: ' + login)
    else:
        if 'login' in request.POST:
            login = request.POST['login']
            log.info('views.confirm() login found in POST: ' + login)
        else:
            if 'login' in request.session:
                login = request.session['login']
                log.info('views.status() login found in session: ' + login)
            else:
                login = psu_sys.get_user(request.META)
                log.info('views.confirm() login not found, defaulting to : ' +
                         login)

    #log.info('views.confirm(), META = ' + str(request.META))

    large_emails = psu_sys.large_emails(login)

    return render_to_response('ghoul/confirm.html',
        {'login': login, 'large_emails': large_emails},
        context_instance=RequestContext(request))
