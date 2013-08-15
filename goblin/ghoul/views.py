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

from goblin.ghoul.forms import FORMS, ConfirmForm, FinalConfirmForm

import celeryconfig

log = logging.getLogger('ghoul.views')

TEMPLATES = {"migrate": "ghoul/form_wizard/step1yes.html",
             "confirm_trans": "ghoul/form_wizard/step1noB.html",
             "forward_notice": "ghoul/form_wizard/step2yes.html",
             "prohibit": "ghoul/form_wizard/step2no.html",
             "mobile": "ghoul/form_wizard/step3.html",
             "confirm": "ghoul/form_wizard/step4no.html"}

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

    if "@" not in forward:
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
    login = get_login(wizard.request)
    sync = presync_cache(login)
    log.info("show_migrate(): " + str(sync))
    return sync

def show_transition(wizard):
    """
    show_transition:
        Check ldap to see if user has the googlePreSync flag set.
        If the flag is not set, return true.
    """
    login = get_login(wizard.request)
    sync = not presync_cache(login)
    log.info("show_transition(): " + str(sync))
    return sync


def show_confirm_trans(wizard):
    """
    show_confirm_trans:
        Check ldap to see if user has the googlePreSync flag set.
        If the flag is not set, return true.
    """
    login = get_login(wizard.request)
    sync = not presync_cache(login)
    log.info("show_confirm_trans(): " + str(sync))
    return sync

def show_forward_notice(wizard):
    """
    show_forward_notice:
        Check the wizard to see if a forward is set
    """
    login = get_login(wizard.request)
    fwd = forward_cache(login)
    log.info("show_forward_notice(): " + str(fwd[0]))
    return fwd[0]

def show_confirm(wizard):
    """
    show_confirm:
        Check ldap to see if the user has the googlePreSync flag set.
        If the flag is set, return true.
    """
    login = get_login(wizard.request)
    sync = presync_cache(login)
    log.info("show_confirm(): " + str(sync))
    return sync

# Memcache Helper Functions

def presync_cache(login, psusys=False):
    if psusys is False:
        psusys = PSUSys()

    if cache.get(login + "_presync", None) is None:
        # Presync
        presync = psusys.presync_enabled(login)
        # Cache presync
        cache.set(login + "_presync", presync, 3600)

    # LDAP returns "0" or "1", we need ints, not strings
    return int(cache.get(login + "_presync"))

def forward_cache(login, psusys=False):
    if psusys is False:
        psusys = PSUSys()
    """
    if cache.get(login + "_fwd", None) is None:
        # Forward
        fwd = get_forward(login, psusys)

        # Set fwd cache
        if fwd[0]:
            cache.set(login + "_fwd", True, 3600)
            cache.set(login + "_fwd_email", fwd[1], 3600)
        elif not fwd[0]:
            cache.set(login + "_fwd", False, 3600)
            cache.set(login + "_fwd_email", False, 3600)

    # LDAP retruns only strings. The _fwd should be an integer
    return (int(cache.get(login + "_fwd")), cache.get(login + "_fwd_email"))
    """
    fwd = get_forward(login, psusys)
    if fwd[0]:
        return (fwd[0], fwd[1])
    else:
        return (fwd[0], "")

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

    # We need to check if the user is in progress as well, and if so, don't let
    # them go through the process again
    if psusys.opt_in_status(login) == "progress":
        return HttpResponseRedirect("/opted_in")

    # Cache data initially, may not be necessary
    # Forward
    forward_cache(login, psusys)

    # Presync
    presync_cache(login, psusys)

    # Redirect to the migration form
    return HttpResponseRedirect("/migrate")

def opted_in(request):
    """
    The user has already opted in, show them the proper message
    """
    return render_to_response('opted_in.html', {
        'page_title': 'Opted In',
    })

def progress(request):
    """
    Show the user the final info and a progress bar of their
    transfer status
    """
    for seskey in request.session.keys():
        del request.session[seskey]

    return render_to_response('ghoul/form_wizard/step5done.html', {
        'page_title': "Opt-In Now Processing",
    })

def missing_google_account(request):
    """
    Error page when the user does not have an account
    """
    return render_to_respons('ghoul/no_gmail_account.html', {
        'page_title': "No google account exists",
    })


class MigrationWizard(SessionWizardView):
    """
    SessionWizardView for the onid->gmail migration
    """

    page_titles = {"confirm_trans": {'page_title': "Current Email Will \
                                                        Not Be Migrated"},
                   "forward_notice": {'page_title': "Notice to Reset Your \
                                                    Forward"},
                   "prohibit": {'page_title': "Prohibited Data Notice"},
                   "mobile": {'page_title': "Reconfigure Email Access"},
                   "confirm": {'page_title': "Confirm"},}

    def dispatch(self, request, *args, **kwargs):
        """
        Overriding WizardView dispatch to force a redirect if a user is
        already opted in.
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
            return HttpResponseRedirect('/opted_in')

        return super(MigrationWizard, self).dispatch(request, *args, **kwargs)

    def get_next_step(self, step=None):
        """
        Hardcoding next step to avoid potential issues with the condition dict
        """

        # Going along with the original method, if we are given none for the
        # step, we can still retrieve it
        if step is None:
            step = self.steps.current

        if step == "migrate":
            login = get_login(self.request)
            if not presync_cache(login):
                return "confirm_trans"
            elif forward_cache(login)[0]:
                return "forward_notice"
            else:
                return "prohibit"
        elif step == "confirm_trans":
            login = get_login(self.request)
            if forward_cache(login)[0]:
                return "forward_notice"
            else:
                return "prohibit"
        elif step == "forward_notice":
            return "prohibit"
        elif step == "prohibit":
            return "mobile"
        elif step == "mobile":
            return "confirm"

        return None

    def get_context_data(self, form, **kwargs):
        context = super(MigrationWizard, self)\
                  .get_context_data(form=form, **kwargs)

        if self.steps.current == "migrate":
            login = get_login(self.request)
            if presync_cache(login):
                context.update({"page_title": "Are You Ready to Move Your ONID \
                                               Mailbox to Google?"})
            else:
                context.update({"page_title": "Are You Ready to Transition Your \
                                               ONID email address to Google"})
        else:
            # Update the page title
            context.update(self.page_titles.get(self.steps.current))

        # Return the email forward if we have one
        if self.steps.current == "forward_notice":
            # Get login, needed for the forward_cache
            login = get_login(self.request)
            context.update({"forward": forward_cache(login)[1]})

        return context

    def get_template_names(self):
        # Given the step is confirm, get the proper template based on user type
        if self.steps.current == "migrate":
            login = get_login(self.request)
            if presync_cache(login):
                return "ghoul/form_wizard/step1yes.html"
            else:
                return "ghoul/form_wizard/step1no.html"
        elif self.steps.current == "confirm":
            login = get_login(self.request)
            if presync_cache(login):
                return "ghoul/form_wizard/step4yes.html"
            else:
                return "ghoul/form_wizard/step4no.html"

        # Return the proper template otherwise
        return [TEMPLATES[self.steps.current]]

    def get_form(self, step=None, data=None, files=None):
        """
        Return the correct form if the step is confirm,
        else let the super method handle it
        """
        if self.steps.next == "confirm":
            login = get_login(self.request)
            if presync_cache(login):
                return ConfirmForm(step=step, data=data, form=form)
            else:
                return FinalConfirmForm(step=step, data=data, form=form)

        # Since we are not on the confirm step, let the super method
        # handle this
        return super(MigrationWizard, self).get_form(step, data, files)

    def done(self, form_list, **kwargs):
        """
        Step5done is the final step of the form, which is just a
        reiteration of all the pages the user just went through.
        """
        login = get_login(self.request)
        presync = presync_cache(login)
        fwd = forward_cache(login)

        # Celery task: copy_email_task
        copy_email_task.apply_async(args=[login, presync, fwd[0], fwd[1]], queue='optin')
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
