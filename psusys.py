from googleimap.imapstat import imapstat
from property import Property
import logging
import logging.config
import simplejson
import memcache
from googleimap.psuldap import psuldap
from time import sleep
import shlex
import subprocess
import os
from memcacheq import MemcacheQueue
import gdata.apps.organization.service
import gdata.apps.service
import gdata.apps.multidomain.client
from gdata.service import BadAuthentication
from gdata.service import CaptchaRequired
from gdata.apps.service import AppsForYourDomainException


class PSUSys:
    def __init__(self):
        self.MAX_MAIL_SIZE = pow(2, 20) * 25
        self.MAX_RETRY_COUNT = 5
        self.large_emails = []
        self.prop = Property(key_file='opt-in.key',
                             properties_file='opt-in.properties')
        self.log = logging.getLogger('goblin.psusys')
        print "Logging default handlers: " + str(self.log.handlers)
        if len(self.log.handlers) == 0:
            # No handlers for this logger, assume logging is not initialized..
            logging.config\
                   .fileConfig('/var/www/goblin/current/etc/logging.conf')
            log = logging.getLogger('goblin.psusys')
            self.setLogger(log)

        self.META_IDENTITY = 'REMOTE_ADDR'

    def setLogger(self, logger):
        self.log = logger

    def large_emails(self, login):
        # verify these values - are these correct for the user we are testing?
        imap_host = self.prop.get('imap.host')
        imap_login = self.prop.get('imap.login')
        imap_password = self.prop.get('imap.password')

        self.log.info('PSUSys.large_emails() login: ' + login)

        ims = imapstat(imap_host, imap_login, imap_password)
        self.log.info('PSUSys.large_emails() imapstat host: ' + imap_host)

        #stat returns:
        # {'mbox_list': [box1, box2...], 'quota': quota, 'quota_used': used}
        stat = ims.stat(login)
        large_emails = []

        if not stat['mbox_list']:
            return large_emails

        # bigmessages returns:
        # { 'box1': [header1, header2...] }
        # where header1, etc are:
        # [{'Recieved': 'recieved header', 'From': 'from header', etc..}]
        msg_list = ims.bigmessages(login,
                                   stat['mbox_list'], self.MAX_MAIL_SIZE)
        for folder in msg_list.keys(): # box1, etc
            for msg in msg_list[folder]: # header1, etc
                large_email = {}
                for key in ['Subject', 'Date', 'From']:
                    if key in msg:
                        large_email[key] = msg[key]
                    else:
                        large_email[key] = 'none'  # why bother?
                large_emails.append(large_email)

        return large_emails

    def presync_enabled(self, login):
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.read.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        self.log.info('presync_enabled(): connecting to LDAP: ' + ldap_host)

        ldap.connect(ldap_host, ldap_login, ldap_password)
        res = ldap.search(searchfilter='uid=' + login,
                          attrlist=['googlePreSync'])

        for (dn, result) in res:
            if "googlePreSync" in result:
                self.log.info('presync_enabled() user: ' + login +
                              ' has a googlePreSync ' +
                              str(result['googlePreSync']))

                if "1" in result["googlePreSync"]:
                    self.log.info('presync_enabled() user: ' + login +
                                  ' has googlePreSync is set')
                    return True
        return False

    def opt_in_already(self, login):
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.read.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)

        ldap.connect(ldap_host, ldap_login, ldap_password)
        res = ldap.search(searchfilter='uid=' + login,
                          attrlist=['googleMailEnabled'])

        for (dn, result) in res:
            if "googleMailEnabled" in result:
                self.log.info('opt_in_alread() user: ' + login +
                              ' has a googleMailEnabled ' +
                              str(result['googleMailEnabled']))

                if "1" in result["googleMailEnabled"]:
                    self.log.info('opt_in_alread() user: ' + login +
                                  ' has googleMailEnabled already set')
                    return True
        return False

    def is_oamed(self, login):
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.read.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        self.log.info('is_oamed(): connecting to LDAP: ' + ldap_host)

        attr = 'googlePreSync'
        ldap.connect(ldap_host, ldap_login, ldap_password)
        res = ldap.search(searchfilter='uid=' + login, attrlist=[attr])

        for (dn, result) in res:
            if attr in result:
                self.log.info('is_oamed() user: ' + login +
                              ' has a ' + attr +
                              ' of ' + str(result[attr]))

                for affiliation in result[attr]:
                    if affiliation in ['SPONSORED', 'SERVICE']:
                        self.log.info('is_oamed() user: ' + login +
                                      ' is not OAMed')
                        return False
        return True

    def get_ldap_attr(self, login, attr):
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.read.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        self.log.info('get_ldap_attr(): connecting to LDAP: ' + ldap_host)

        ldap.connect(ldap_host, ldap_login, ldap_password)
        res = ldap.search(searchfilter='uid=' + login, attrlist=['mailHost'])

        for (dn, result) in res:
            if attr in result:
                return str(result[attr])

    def route_to_google_null(self, login):
        self.log.info('route_to_google(): routing mail to google for user: ' +
                      login)
        sleep(1)

    def is_allowed(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        # Does this user have an elligible account
        if not self.is_oamed(login):
            return False

        # Is this user explicitly denied
        deny_users = prop.get('deny.users')
        if login in deny_users:
            return False

        # Is this user explicitly allowed
        allow_all = prop.get('allow.all')
        if allow_all == 'False':
            allow_users = prop.get('allow.users')
            if login in allow_users:
                return True
        else:
            return True

        return False

    # Temporary hack till Adrian sorts-out the access issues for modifying LDAP
    def route_to_google_hack(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        mc.set('gmx_done.' + login, None)
        mcq = MemcacheQueue('to_google', mc)
        mcq.add(login)
        res = mc.get('gmx_done.' + login)
        while res is None:
            res = mc.get('gmx_done.' + login)
            print 'Waiting for ' + login + ' to route to Google'
            sleep(10)

    def route_to_google_old(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        self.log.info('route_to_google_old(): Routing mail to Google for user: ' +
                      login)
        ldap_host = prop.get('ldap.write.host')
        ldap_login = prop.get('ldap.login')
        ldap_password = prop.get('ldap.password')

        cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host +\
              ' -D ' + ldap_login + " -w " + ldap_password

        # Launch a Subprocess here to re-route email
        input = '''
dn: uid=%s, ou=people, dc=pdx, dc=edu
changetype: modify
delete: mailHost
mailHost: cyrus.psumail.pdx.edu
-
add: mailHost
mailHost: gmx.pdx.edu
''' % login

        syncprocess = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE)

        syncprocess.communicate(input)

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info("route_to_google_old(): continuing to route mail to\
                          Google for user: " + login)

        if syncprocess.returncode == 0:
            self.log.info('route_to_google_old(): success for user: ' + login)
            return True
        else:
            self.log.info('route_to_google(): failed for user: ' + login)
            return False

    def route_to_psu(self, login):
        self.update_mailHost(login, 'cyrus.psumail.pdx.edu')
        self.update_mailRoutingAddress(login, 'odin.pdx.edu')

    def route_to_google(self, login):
        status = self.update_mailHost(login, 'gmx.pdx.edu')
        retry_count = 0
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            self.log.error("route_to_google(): mailHost: Retrying LDAP update")
            status = self.update_mailHost(login, 'gmx.pdx.edu')
            retry_count += 1

        status = self.update_mailRoutingAddress(login, 'pdx.edu')
        retry_count = 0
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            self.log.error("route_to_google(): \
                           mailRoutingAddress: Retrying LDAP update")
            status = self.update_mailRoutingAddress(login, 'pdx.edu')
            retry_count += 1

    def update_mailHost(self, login, deliveryHost):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        self.log.info('update_mailHost(): Routing mail to psu for user: ' +
                      login)
        ldap_host = prop.get('ldap.write.host')
        ldap_login = prop.get('ldap.login')
        ldap_password = prop.get('ldap.password')

        cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host +\
              ' -D ' + ldap_login + " -w " + ldap_password

        # Launch a Subprocess here to re-route email
        input = '''
dn: uid=%s, ou=people, dc=pdx, dc=edu
changetype: modify
replace: mailHost
mailHost: %s
''' % (login, deliveryHost)

        syncprocess = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE)

        syncprocess.communicate(input)

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info('update_mailHost(): continuing to route mail to \
                          psu for user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('update_mailHost(): success for user: ' + login)
            return True
        else:
            self.log.info('update_mailHost(): failed for user: ' + login)
            return False

    def update_mailRoutingAddress(self, login, deliveryAddr):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        self.log.info('update_mailRoutingAddress(): \
                      Updating mailRoutingAddress for user: ' + login)
        ldap_host = prop.get('ldap.write.host')
        ldap_login = prop.get('ldap.login')
        ldap_password = prop.get('ldap.password')

        cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host +\
              ' -D ' + ldap_login + " -w " + ldap_password

        # Launch a Subprocess here to re-route email
        input = '''
dn: uid=%s, ou=people, dc=pdx, dc=edu
changetype: modify
replace: mailRoutingAddress
mailRoutingAddress: %s@%s
''' % (login, login, deliveryAddr)

        syncprocess = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE)

        syncprocess.communicate(input)

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info('update_mailRoutingAddress(): \
                          Continuing to update mailRoutingAddress for user: ' +
                          login)

        if syncprocess.returncode == 0:
            self.log.info('update_mailRoutingAddress(): success for user: ' +
                          login)
            return True
        else:
            self.log.info('update_mailRoutingAddress(): failed for user: ' +
                          login)
            return False

    # Temporary hack till Adrian sorts-out the access issues for modifying LDAP
    def route_to_psu_hack(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        mc.set('psu_done.' + login, None)
        mcq = MemcacheQueue('to_psu', mc)
        mcq.add(login)
        res = mc.get('psu_done.' + login)
        while res is None:
            res = mc.get('psu_done.' + login)
            print 'Waiting for ' + login + ' to route to PSU'
            sleep(10)

    def route_to_google_future(self, login):
        self.log.info('route_to_google_future(): routing mail to google for user: ' +
                      login)
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        ldap.connect(ldap_host, ldap_login, ldap_password)

        dn = 'uid=' + login + ', ou=people, dc=pdx, dc=edu'
        ldap.mod_attribute(dn, 'mailHost', 'gmx.pdx.edu')

    def route_to_psu_future(self, login):
        ldap = psuldap('/vol/certs')
        ldap_host = self.prop.get('ldap.host')
        ldap_login = self.prop.get('ldap.login')
        ldap_password = self.prop.get('ldap.password')
        ldap.connect(ldap_host, ldap_login, ldap_password)

        dn = 'uid=' + login + ', ou=people, dc=pdx, dc=edu'
        ldap.mod_attribute(dn, 'mailHost', 'cyrus.psumail.pdx.edu')

    def get_user(self, meta):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)

        login = None
        if self.META_IDENTITY in meta:
            key = meta[self.META_IDENTITY]
            login = mc.get(key)
        else:
            self.log.info('get_user(), failed to find: ' +
                          self.META_IDENTITY + ' in META')

        if login is None:
            login = 'dennis'
            self.log.info('get_user(), defaulting to user ' +
                          login)
        else:
            self.log.info('get_user(), found user ' + login +
                          ' in memcache')
        return login

    def set_user(self, login, meta):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)

        if self.META_IDENTITY in meta:
            key = meta[self.META_IDENTITY]
            mc.set(key, login)
            self.log.info('set_user(), set user ' + login +
                          ' in memcache')
        else:
            self.log.info('set_user(), failed to find: ' +
                          self.META_IDENTITY + ' in META')

    def send_conversion_email_null(self, login):
        addr = login + '@pdx.edu'
        self.log.info('send_conversion_email_null(): sending mail to user: ' + addr)
        sleep(1)
        # Send the conversion confirmation email to the user
        # Launch a Subprocess here to send email

    def send_conversion_email_in_progress(self, login, root_dir):
        self.log.info('send_conversion_email_in_progress(): \
                      sending mail to user: ' + login)
        # Send the conversion confirmation email to the user
        # Launch a Subprocess here to send email
        cmd = os.path.join(root_dir, 'conversion_email_in_progress')

        syncprocess = subprocess.Popen([cmd, login],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        sync_output = syncprocess.communicate()

        if syncprocess.returncode == 0:
            self.log.info('send_conversion_email_in_progress(): \
                          success for user: ' + login)
            return True
        else:
            self.log.info('send_conversion_email_in_progress(): \
                          failed for user: ' + login + '\n' +
                          sync_output[1])
            return False

    def send_forward_email(self, login, fwd_email):
        self.log.info("send_forward_email(): sending mail to user: " + login)

        # Send the forward email to the user
        # More perl
        cmd = '/var/www/goblin/current/conversion_email_forward ' + login + " '" + fwd_email + "'"

        syncprocess = subprocess.Popen(shlex.split(cmd),
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        sync_output = syncprocess.communicate()

        if syncprocess.returncode == 0:
            self.log.info('send_forward_email(): \
                          success for user: ' + login)
            return True
        else:
            self.log.info('send_forward_email(): \
                          failed for user: ' + login + '\n' +
                          sync_output[1])
            return False

    def send_conversion_email_psu(self, login):
        self.log.info('send_conversion_email_psu(): sending mail to user: ' +
                      login)
        # Send the conversion confirmation email to the user
        # Launch a Subprocess here to send email
        cmd = '/var/www/goblin/current/conversion_email_psu ' + login

        syncprocess = subprocess.Popen(shlex.split(cmd))

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info('send_conversion_email_psu(): \
                          continuing to send mail for user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('send_conversion_email_psu(): success for user: ' +
                          login)
            return True
        else:
            self.log.info('send_conversion_email_psu(): failed for user: ' +
                          login)
            return False

    def send_conversion_email_google(self, login):
        self.log.info('send_conversion_email_google(): sending mail to user: '
                      + login)
        # Send the conversion confirmation email to the user
        # Launch a Subprocess here to send email
        cmd = '/var/www/goblin/current/conversion_email_google ' + login

        syncprocess = subprocess.Popen(shlex.split(cmd))

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info('send_conversion_email_google(): \
                          continuing to send mail for user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('send_conversion_email_google(): \
                          success for user: ' + login)
            return True
        else:
            self.log.info('send_conversion_email_google(): failed for user: ' +
                          login)
            return False

    def enable_gmail_null(self, login):
        self.log.info('enable_gail_null(): Enabling gmail for user: ' + login)
        # Enable gmail here
        sleep(1)

    def is_gmail_enabled(self, login):
        self.log.info('is_gmail_enabled(): \
                      Checking if gmail is enabled for user: ' + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.organization\
                            .service.OrganizationService(email=email,
                                                         domain=domain,
                                                         password=pw)
        retry_count = 0
        status = False
        result = False
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            try:
                client.ProgrammaticLogin()
                customerId = client.RetrieveCustomerId()["customerId"]
                userEmail = login + '@' + domain
                result = (client
                          .RetrieveOrgUser(customerId,
                                           userEmail)['orgUnitPath'] == 'ONID')
                status = True
            except CaptchaRequired:
                self.log.error('is_gmail_enabled(): Captcha being requested')
                sleep(1)
            except BadAuthentication:
                self.log.error('is_gmail_enabled(): Authentication Error')
                sleep(1)
            except Exception, e:
                self.log.error('is_gmail_enabled(): Exception occured: ' +
                               str(e))
                sleep(1)
                # Retry if not an obvious non-retryable error
            retry_count += 1

        return result

    def google_account_status(self, login):
        self.log.info('google_account_status(): \
                      Querying account status for user: ' + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')
        useremail = login + '@' + domain

        client = gdata.apps.multidomain\
                           .client.MultiDomainProvisioningClient(domain=domain)
        retry_count = 0
        status = False
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            try:
                client.ClientLogin(email=email, password=pw, source='apps')
                userDisabled = client.RetrieveUser(useremail).suspended
                if userDisabled == 'false':
                    return {"exists": True, "enabled": True}
                elif userDisabled == 'true':
                    return {"exists": True, "enabled": False}
                else:
                    return {"exists": False, "enabled": False}

            except AppsForYourDomainException, e:
                if e.error_code == 1301:
                    self.log.error('google_account_status(): \
                                   User %s does not exist' % login)
                    return {"exists": False, "enabled": False}

            except(CaptchaRequired):
                self.log.error('google_account_status(): \
                               Captcha being requested')

            except(BadAuthentication):
                self.log.error('google_account_status(): \
                               Authentication Error')

            except Exception, e:
                self.log.error('google_account_status(): \
                               Exception occured: ' + str(e))
                # Retry if not an obvious non-retryable error
                sleep(1)

            retry_count += 1

    def enable_google_account(self, login):
        self.log.info('enable_google_account(): \
                      Enabling account for user: ' + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.multidomain\
                           .client.MultiDomainProvisioningClient(domain=domain)
        retry_count = 0
        status = False
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            try:
                client.ClientLogin(email=email, password=pw, source='apps')
                userDisabled = client.RestoreUser(login).suspended
                if userDisabled == 'false':
                    status = True

            except AppsForYourDomainException, e:
                if e.error_code == 1301:
                    self.log.error('enable_google_account(): \
                                   User %s does not exist' % login)
                    status = True

            except(CaptchaRequired):
                self.log.error('enable_google_account(): \
                               Captcha being requested')

            except(BadAuthentication):
                self.log.error('enable_google_account(): Authentication Error')

            except Exception, e:
                self.log.error('enable_google_account(): Exception occured: ' +
                               str(e))
                # Retry if not an obvious non-retryable error
                sleep(1)

            retry_count = retry_count + 1

    def disable_google_account(self, login):
        self.log.info('disable_google_account(): Disabling account for user: '
                      + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.multidomain\
                           .client.MultiDomainProvisioningClient(domain=domain)
        retry_count = 0
        status = False
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            try:
                client.ClientLogin(email=email, password=pw, source='apps')
                userDisabled = client.SuspendUser(login).suspended
                if userDisabled == 'true':
                    status = True

            except AppsForYourDomainException, e:
                if e.error_code == 1301:
                    self.log.error('disable_google_account(): \
                                   User %s does not exist' % login)
                    status = True

            except(CaptchaRequired):
                self.log.error('disable_google_account(): \
                               Captcha being requested')

            except(BadAuthentication):
                self.log.error('disable_google_account(): \
                               Authentication Error')

            except Exception, e:
                self.log.error('disable_google_account(): Exception occured: ' +
                               str(e))
                # Retry if not an obvious non-retryable error
                sleep(1)

            retry_count += 1

    def retrieve_orgunit(self, login):
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.organization.service.OrganizationService(email=email, domain=domain, password=pw)
        client.ProgrammaticLogin()
        customerId = client.RetrieveCustomerId()["customerId"]
        userEmail = login + '@' + domain
        old_org  = client.RetrieveOrgUser( customerId, userEmail)

        return old_org

    def enable_gmail(self, login):
        retry_count = 0
        status = False
        old_orig = self.retrieve_orgunit(login)

        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            self.gmail_set_active(login)
            if self.is_gmail_enabled(login):
                status = True
            retry_count += 1

        return old_orig

    def gmail_set_active(self, login):
        self.log.info('gmail_set_active(): Enabling gmail for user: ' + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.organization.service\
                                        .OrganizationService(email=email,
                                                             domain=domain,
                                                             password=pw)
        retry_count = 0
        status = False
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            try:
                client.ProgrammaticLogin()
                customerId = client.RetrieveCustomerId()["customerId"]
                userEmail = login + '@' + domain
                client.UpdateOrgUser(customerId, userEmail, 'ONID')
                status = True
            except CaptchaRequired:
                self.log.error('gmail_set_active(): Captcha being requested')
                sleep(1)
            except BadAuthentication:
                self.log.error('gmail_set_active(): Authentication Error')
                sleep(1)
            except Exception, e:
                self.log.error('gmail_set_active(): Exception occured: ' +
                               str(e))
                sleep(1)
                # Retry if not an obvious non-retryable error
            retry_count += 1
        return status

    def disable_gmail(self, login, old_org='NO_SERVICES'):
        self.log.info('disable_gmail(): Disabling gmail for user: ' + login)
        email = self.prop.get('google.email')
        domain = self.prop.get('google.domain')
        pw = self.prop.get('google.password')

        client = gdata.apps.organization.service\
                                        .OrganizationService(email=email,
                                                             domain=domain,
                                                             password=pw)
        client.ProgrammaticLogin()
        customerId = client.RetrieveCustomerId()["customerId"]
        userEmail = login + '@' + domain
        client.UpdateOrgUser(customerId, userEmail, old_org['orgUnitPath'])

    def sync_email_null(self, login):
        self.log.info('sync_email_null(): syncing user: ' + login)
        sleep(1)

    def sync_email(self, login, extra_opts='', max_process_time=0):
        self.log.info('sync_email(): syncing user: ' + login)
        imap_host = self.prop.get('imap.host')
        imap_login = self.prop.get('imap.login')
        google_domain = self.prop.get('google.domain')

        imapsync_dir = "/opt/google-imap/"
        imapsync_cmd = imapsync_dir + "imapsync"
        cyrus_pf = imapsync_dir + "cyrus.pf"
        google_pf = imapsync_dir + "google-prod.pf"

        exclude_list = "'^Shared Folders|^Other Users|^junk-mail$|^Junk$|^junk$|^JUNK$|^Spam$|^spam$|^SPAM$'"
        whitespace_cleanup = " --regextrans2 's/[ ]+/ /g' --regextrans2 's/\s+$//g' --regextrans2 's/\s+(?=\/)//g' --regextrans2 's/^\s+//g' --regextrans2 's/(?=\/)\s+//g'"
        folder_cases = " --regextrans2 's/^drafts$/[Gmail]\/Drafts/i' --regextrans2 's/^trash$/[Gmail]\/Trash/i' --regextrans2 's/^(sent|sent-mail|Sent Messages)$/[Gmail]\/Sent Mail/i'"
        command = imapsync_cmd + " --pidfile /tmp/imapsync-" + login + ".pid --host1 " + imap_host + " --port1 993 --user1 " + login + " --authuser1 " + imap_login + " --passfile1 " + cyrus_pf + " --host2 imap.gmail.com --port2 993 --user2 " + login + "@" + google_domain + " --passfile2 " + google_pf + " --ssl1 --ssl2 --maxsize 26214400 --authmech1 PLAIN --authmech2 XOAUTH --sep1 '.' --exclude " + exclude_list + folder_cases + whitespace_cleanup + extra_opts

        self.log.info(command)

        if extra_opts == '':
            log_file_name = '/var/log/imapsync/imapsync-' + login + '.log'
        else:
            log_file_name = '/var/log/imapsync/imapsync-' + login + '-delete.log'
        syncprocess = subprocess.Popen(shlex.split(command),
                                       stdout=open(log_file_name, 'w'))
    # While the process is running, and we're under the time limit
        process_time = 0.0
        while (syncprocess.poll() is None):
            sleep(30)
            process_time += 0.5
            if max_process_time > 0 and int(process_time) > max_process_time:
                syncprocess.terminate()
                self.log.info('sync_email(): \
                              terminating sync due to max process time limit \
                              for user: ' + login)
                return True
            self.log.info('sync_email(): continuing to sync user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('sync_email(): success syncing user: ' + login)
            return True
        else:
            self.log.info('sync_email(): failed syncing user: ' + login)
            return False

    def sync_email_delete2(self, login, max_process_time=0):
        return self\
               .sync_email(login,
                           extra_opts=' --delete2 --delete2folders --fast ',
                           max_process_time=max_process_time)

    def sync_email_delete2_obs(self, login):
        self.log.info('sync_email_delete2_obs(): syncing user: ' + login)
        imapsync_cmd = '/opt/google-imap/imapsync'
        imap_host = self.prop.get('imap.host')
        imap_login = self.prop.get('imap.login')
        cyrus_pf = '/opt/google-imap/cyrus.pf'
        google_pf = '/opt/google-imap/google-prod.pf'

        command = imapsync_cmd + " --pidfile /tmp/imapsync-full-" + login + ".pid --host1 " + imap_host + " --port1 993 --user1 " + login + " --authuser1 " + imap_login + " --passfile1 " + cyrus_pf + " --host2 imap.gmail.com --port2 993 --user2 " + login + "@" + 'pdx.edu' + " --passfile2 " + google_pf + " --ssl1 --ssl2 --maxsize 26214400 --delete2 --delete2folders --authmech1 PLAIN --authmech2 XOAUTH -sep1 '/' --exclude '^Shared Folders' "
        log_file_name = '/var/log/imapsync/imapsync-' + login + '-delete.log'
        syncprocess = subprocess.Popen(shlex.split(command),
                                       stdout=open(log_file_name, 'w'))

        self.log.info('sync_email_delete2_obs(): command: ' + command)
    # While the process is running, and we're under the time limit
        while (syncprocess.poll() is None):
            sleep(30)
            self.log.info('sync_email_delete2_obs(): continuing to sync user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('sync_email_delete2_obs(): success syncing user: ' + login)
            return True
        else:
            self.log.info('sync_email_delete2_obs(): failed syncing user: ' + login)
            return False

        # Call sync here

    def is_processing(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        key = 'email_copy_progress.' + login
        cached_data = mc.get(key)

        if (cached_data is None):
            return False
        return True

    def is_web_suspended(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        web_suspended = prop.get('web.suspended')

        if web_suspended == 'True':
            self.log.info('is_web_suspended(): user: ' + login +
                          " visited while the opt-in web site was suspended")
            return True

        return False

    def copy_progress(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)

        #cache_key = "copy_progress_%s" % (request.GET['login', 'default'])
        key = 'email_copy_progress.' + login
        cached_data = mc.get(key)

        if (cached_data is None):
            cached_data = 0
        #data = simplejson.dumps(cached_data)
        data = simplejson.dumps(cached_data)
        self.log.info('copy_progress() called, memcache_url: ' +
                      memcache_url + ", data: " + data + ', login: ' + login)

        return data
        #return HttpResponse(simplejson.dumps(27))

    def set_googleMailEnabled(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')
        self.log.info('set_googleMailEnabled(): setting LDAP attribute for user: ' +
                      login)
        ldap_host = prop.get('ldap.write.host')
        ldap_login = prop.get('ldap.login')
        ldap_password = prop.get('ldap.password')

        cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host +\
              ' -D ' + ldap_login + " -w " + ldap_password

        # Launch a Subprocess here to re-route email
        input = '''
dn: uid=%s, ou=people, dc=orst.edu
changetype: modify
replace: mailHost
googleMailEnabled: 1
''' % (login)

        syncprocess = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE)

        syncprocess.communicate(input)

        while (syncprocess.poll() is None):
            sleep(3)
            self.log.info('set_googleMailEnabled(): continuing to write to attribute \
                          psu for user: ' + login)

        if syncprocess.returncode == 0:
            self.log.info('set_googleMailEnabled(): success for user: ' + login)
            return True
        else:
            self.log.info('set_googleMailEnabled(): failed for user: ' + login)
            return False

    def copy_email_task(self, login, sync, forward, fwd_email):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        # Logging is occuring within celery worker here
        log = logging.getLogger('')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        psu_sys = PSUSys()

        log.info("copy_email_task(): processing user: " + login)
        key = 'email_copy_progress.' + login

        account_status = psu_sys.google_account_status(login)

        # Check to make sure the user has a Google account
        if account_status.get("exists", False) is False:
            log.info("presync_email_task(): user does not exist in Google: " +
                     login)
            return(True)

        # Check for LDAP mail forwarding already (double checking), if
        # already opt'd-in, then immediately return and mark as complete.

        if psu_sys.opt_in_already(login):
            log.info("copy_email_task(): has already completed opt-in: " +
                     login)
            mc.set(key, 100)
            # Done?
            return(True)
        else:
            log.info("copy_email_task(): has not already completed opt-in: " +
                     login)
            mc.set(key, 40)

        # We temporarily enable suspended accounts for
        # the purposes of synchronization
        if account_status.get("enabled", False) is False:
            log.info("presync_email_task(): temporarily enabling account: " +
                     login)
            # Enable account if previously disabled
            # XXX: This function doesn't seem to do anything, incomplete?
            psu_sys.enable_google_account(login)
            mc.set(key, 45)

        # Send conversion info email to users Google account
        log.info("copy_email_task(): conversion in progress email: " + login)
        if sync:
            log.info("update_email_task(): sending migration in progress email")
            psu_sys.send_conversion_email_in_progress(login, '/var/www/goblin/current/')

        # Enable Google email for the user
        # This is the last item that the user should wait for.

        psu_sys.enable_gmail(login)
        mc.set(key, 50)

        # Synchronize email to Google (and wait)
        if psu_sys.presync_enabled(login):
	    log.info("copy_email_task(): first pass syncing email: " + login)
            status = psu_sys.sync_email_delete2(login)
            retry_count = 0
            while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
                log.info("copy_email_task(): Retry of first pass syncing email: " +
                         login)
                status = psu_sys.sync_email_delete2(login)
                sleep(4 ** retry_count)
                retry_count = retry_count + 1

        mc.set(key, 60)

        # Switch routing of email to flow to Google
        log.info("copy_email_task(): Routing email to Google: " + login)
        #psu_sys.route_to_google(login)
        # Perl script to run
        cmd = '/var/www/goblin/current/bin/set-cyrus-fwd.pl'
        # Imap config file
        config = '/var/www/goblin/current/etc/imap_fwd.cfg'
        # Subprocess
        results = subprocess.Popen(['perl', cmd, config, login])
        # Communicate to get (stdout, stderr)
        output = results.communicate()
        log.info("set-fwd: " + str(output))
        mc.set(key, 70)

        # Final email sync
        if psu_sys.presync_enabled(login)):
            log.info("copy_email_task(): second pass syncing email: " + login)
            status = psu_sys.sync_email(login)
            retry_count = 0
            while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
                log.info("copy_email_task(): Retry of second pass syncing email: "
                         + login)
                status = psu_sys.sync_email(login)
                sleep(4 ** retry_count)
                retry_count = retry_count + 1

        mc.set(key, 80)

        # The folowing items occur without the user waiting.

        # Send conversion info email to users Google account
        log.info("copy_email_task(): sending post conversion email to Google: "
                 + login)
        psu_sys.send_conversion_email_google(login)

        # Send conversion info email to users PSU account
        log.info("copy_email_task(): sending post conversion email to PSU: " +
                 login)
        psu_sys.send_conversion_email_psu(login)

        # Send forward email info if a forward is set
        if forward:
            log.info("copy_email_task(): sending forward information email")
            psu_sys.send_forward_email(login, fwd_email)

        # If the account was disabled, well...
        if account_status.get("enabled", False) is False:
            log.info("presync_email_task(): disabling account: " + login)

            # Enable account if previously disabled
            psu_sys.disable_google_account(login)
            mc.set(key, 90)

        # update LDAP to reflect the newly created account
        psu_sys.set_googleMailEnabled(login)
        mc.set(key, 100)

        return(True)

    def presync_email_task(self, login):
        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        # Logging is occuring within celery worker here
        log = logging.getLogger('')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        psu_sys = PSUSys()

        # Time is in minutes
        max_process_time = 60

        log.info("presync_email_task(): processing user: " + login)
        optin_key = 'email_copy_progress.' + login
        key = 'email_presync_progress.' + login

        # Check to see if an opt-in task is running--if so, exit
        if mc.get(optin_key) is not None:
            log.info("presync_email_task(): user currently opting-in: " +
                     login)
            return(True)

        account_status = psu_sys.google_account_status(login)

        # Check to make sure the user has a Google account
        if account_status.get("exists", False) is False:
            log.info("presync_email_task(): user does not exist in Google: " +
                     login)
            return(True)

        # Check for LDAP mail forwarding already (double checking), if
        # already opt'd-in, then immediately return and mark as complete.

        if (psu_sys.opt_in_already(login)):
            log.info("presync_email_task(): has already completed opt-in: " +
                     login)
            return(True)
        else:
            log.info("presync_email_task(): has not already completed opt-in: "
                     + login)

        # We temporarily enable suspended accounts for
        # the purposes of synchronization
        if account_status["enabled"] is False:
            log.info("presync_email_task(): temporarily enabling account: " +
                     login)
            # Enable account if previously disabled
            psu_sys.enable_google_account(login)

        # Enable Google email for the user
        log.info("presync_email_task(): temporarily enabling Google mail: " +
                 login)
        old_org = psu_sys.enable_gmail(login)

        # Synchronize email to Google (and wait)
        log.info("presync_email_task(): syncing email: " + login)
        status = psu_sys.sync_email_delete2(login,
                                            max_process_time=max_process_time)
        retry_count = 0
        while (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            log.info("presync_email_task(): Retry syncing email: " + login)
            status = psu_sys\
                     .sync_email_delete2(login,
                                         max_process_time=max_process_time)
            sleep(4 ** retry_count)
            retry_count = retry_count + 1

        # Synchronization complete

        # Disable Google email
        log.info("presync_email_task(): disabling Google mail: " + login)
        psu_sys.disable_gmail(login,old_org)

        if account_status["enabled"] is False:
            log.info("presync_email_task(): disabling account: " + login)
            # Enable account if previously disabled
            psu_sys.disable_google_account(login)

        # Call it good.

        return(True)

    def recover_copy_email_task(self, login):
        '''
        Recover from case where celery task has died unexpectantly.
        Don't do delete2 phase.
        '''

        prop = Property(key_file='opt-in.key',
                        properties_file='opt-in.properties')

        # Logging is occuring within celery worker here
        log = logging.getLogger('')
        memcache_url = prop.get('memcache.url')
        mc = memcache.Client([memcache_url], debug=0)
        psu_sys = PSUSys()

        log.info("copy_email_task(): processing user: " + login)
        key = 'email_copy_progress.' + login

        # Check for LDAP mail forwarding already (double checking), if
        # already opt'd-in, then immediately return and mark as complete.

        if (psu_sys.opt_in_already(login)):
            log.info("copy_email_task(): has already completed opt-in: " +
                     login)
            # mc.set(key, 100)
            #return(True)
            mc.set(key, 40)
        else:
            log.info("copy_email_task(): has not already completed opt-in: " +
                     login)
            mc.set(key, 40)

        # Enable Google email for the user
        # This is the last item that the user should wait for.

        psu_sys.enable_gmail(login)
        mc.set(key, 50)

        '''
        # Synchronize email to Google (and wait)
        log.info("copy_email_task(): first pass syncing email: " + login)
        status = psu_sys.sync_email_delete2(login)
        retry_count = 0
        if (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            status = psu_sys.sync_email_delete2(login)
            sleep(4 ** retry_count)
        '''
        mc.set(key, 60)

        # Switch routing of email to flow to Google

        log.info("copy_email_task(): Routing email to Google: " + login)
        psu_sys.route_to_google(login)
        mc.set(key, 70)

        # Final email sync
        log.info("copy_email_task(): second pass syncing email: " + login)
        status = psu_sys.sync_email(login)
        retry_count = 0
        if (status is False) and (retry_count < self.MAX_RETRY_COUNT):
            status = psu_sys.sync_email(login)
            sleep(4 ** retry_count)
            retry_count = retry_count + 1

        mc.set(key, 80)

        # The folowing items occur without the user waiting.

        # Send conversion info email to users Google account
        log.info("copy_email_task(): sending post conversion email to Google: "
                 + login)
        psu_sys.send_conversion_email_google(login)

        # Send conversion info email to users PSU account
        log.info("copy_email_task(): sending post conversion email to PSU: " +
                 login)
        psu_sys.send_conversion_email_psu(login)

        mc.set(key, 100)

        return(True)
