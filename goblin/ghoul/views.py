from subprocess import PIPE, Popen

from django.conf import settings
from django.core.cache import cache
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

def get_forward(login, psusys):
    """
    forward_set:
        Shell out to a perl script to see if the user has a forward setup
    """
    get_fwd = '/var/www/goblin/current/bin/get-cyrus-fwd.pl'
    fwd_cfg = '/var/www/goblin/current/etc/imap_fwd.cfg'
    forward = Popen(['perl', get_fwd, fwd_cfg, login],
                    stdout=PIPE).communicate()[0]

    # Now to handle the information returned
    location = psusys.prop.get('imap.host')
    location_str = "Could not connect to mail server %s, please try again." %\
                   location

    # If wizard.form is not set or the perl script returns the location
    # string, return False
    if forward in [None, location_str]:
        return (False,)

    # If the word none is found within the output of the perl script,
    # return False
    if 'none' in forward:
        return (False,)

    # If we are given any other response by the perl script,
    # return True
    return (True, forward)

def get_login(request):
    """
    Get user account name

    This comes from the various methods
    """

    if 'REMOTE_USER' in request.META:
        login = lower(request.META['REMOTE_USER'])
        request.session['login'] = login
    elif 'login' in request.POST:
        login = lower(request.POST['login'])
        request.session['login'] = login
    elif 'login' in request.session:
        login = request.session['login']

    return login

def show_migrate(wizard):
    """
    show_migrate:
        Check ldap to see if the user has the googlePreSync flag set.
        If the flag is set, return true.
    """
    sync = presync_cache()
    log.info("show_migrate(): " + str(sync))
    return sync

def show_transition(wizard):
    """
    show_transition:
        Check ldap to see if user has the googlePreSync flag set.
        If the flag is not set, return true.
    """
    sync = not presync_cache()
    log.info("show_transition(): " + str(sync))
    return sync


def show_confirm_trans(wizard):
    """
    show_confirm_trans:
        Check ldap to see if user has the googlePreSync flag set.
        If the flag is not set, return true.
    """
    sync = not presync_cache()
    log.info("show_confirm_trans(): " + str(sync))
    return sync

def show_forward_notice(wizard):
    """
    show_forward_notice:
        Check the wizard to see if a forward is set
    """
    fwd = forward_cache()
    log.info("show_forward_notice(): " + str(fwd[0]))
    return fwd[0]

def show_confirm(wizard):
    """
    show_confirm:
        Check ldap to see if the user has the googlePreSync flag set.
        If the flag is set, return true.
    """
    sync = presync_cache()
    log.info("show_confirm(): " + str(sync))
    return sync

# Memcache Helper Functions

def presync_cache(psusys=False):
    if psusys is False:
        psusys = PSUSys()

    if cache.get(login + "_presync", None) is None:
        # Presync
        presync = psusys.presync_enabled(login)
        # Cache presync
        cache.set(login + "_presync", presync)

    return cache.get(login + "_presync")

def forward_cache(psusys=False):
    if psusys is False:
        psusys = PSUSys()

    if cache.get(login + "_fwd", None) is None:
        # Forward
        fwd = get_forward(login, psusys)

        # Set fwd cache
        if fwd[0]:
            cache.set(login + "_fwd", True)
            cache.set(login + "_fwd_email", fwd[1])
        elif not fwd[0]:
            cache.set(login + "_fwd", False)
            cache.set(login + "_fwd_email", False)

    return (cache.get(login + "_fwd"), cache.get(login + "_fwd_email"))

def bounce(request):
    """
    Determine if the user should fill out the form or not

    Send them to the "You've done this already" page if not
    Send them to /migrate if they haven't
    """

    # Initially we need a PSUSys object to grab all the info
    # about the user
    psusys = PSUSys()

    # Using the PSUSys we need:
    # login
    login = get_login(request)

    # Check if the user has opt'd in already,
    # if they have, redirect them to the appropriate page
    if psusys.opt_in_already(login):
        return HttpResponseRedirect("/opted_in")

    # Forward
    forward_cache(psusys)

    # Presync
    presync_cache(psusys)

    # Redirect to the migration form
    return HttpResponceRedirect("/migrate")

def progress(request):
    """
    Show the user the final info and a progress bar of their
    transfer status
    """
    for seskey in request.session.keys():
        del request.session[seskey]

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
    SessionWizardView for the onid->gmail migration
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

    def get_context_data(self, form, **kwargs):
        context = super(MigrationWizard, self)\
                  .get_context_data(form=form, **kwargs)

        # Update the page title
        context.update(self.page_titles.get(self.steps.current))

        # Return the email forward if we have one
        if self.steps.current == "forward_notice":
            context.update({"forward": forward_cache[1]})

        return context

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def done(self, form_list, **kwargs):
        """
        Step5done is the final step of the form, which is just a
        reiteration of all the pages the user just went through.
        """
        # Celery task: copy_email_task
        copy_email_task.apply_async(args=[self.login, self.presync, self.forward, self.fwd_email], queue='optin')
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
