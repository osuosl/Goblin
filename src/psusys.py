from imapstat import imapstat
from psuproperties import Property
import logging
import simplejson
import memcache
from psuldap import psuldap
from time import sleep
import shlex, subprocess
from memcacheq import MemcacheQueue
import gdata.apps.organization.service
import gdata.apps.service
from gdata.service import BadAuthentication
from gdata.service import CaptchaRequired
from gdata.apps.service import AppsForYourDomainException


class PSUSys:
	def __init__(self):
		self.MAX_MAIL_SIZE = pow(2,20) * 25
		self.MAX_RETRY_COUNT = 5
		self.prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		self.log = logging.getLogger('goblin.psusys')
		print "Logging default handlers: " + str(self.log.handlers)
		if len(self.log.handlers) == 0:
			# No handlers for this logger, assume logging is not initialized..
			logging.config.fileConfig('/vol/goblin/etc/logging.conf')
			log = logging.getLogger('goblin.psusys')
			self.setLogger(log)

		self.META_IDENTITY = 'REMOTE_ADDR'
		
	def setLogger(self, logger):
		self.log = logger
		
	def large_emails(self, login):
		imap_host = self.prop.getProperty('imap.host')
		imap_login = self.prop.getProperty('imap.login')
		imap_password = self.prop.getProperty('imap.password')
		self.log.info('PSUSys.large_emails() login: ' + login)
		
		ims = imapstat( imap_host, imap_login, imap_password )
		self.log.info('PSUSys.large_emails() imapstat host: ' + imap_host)
		stat = ims.stat(login)
		msg_list = ims.bigmessages(login, stat['mbox_list'], self.MAX_MAIL_SIZE )
		large_emails = []
		for folder in msg_list.keys():
			for msg in msg_list[folder]:
				large_email = {}
				large_emails.append(large_email)
				for key in ['Subject', 'Date', 'From']:
					if key in msg:
						large_email[key] = msg[key]
					else:
						large_email[key] = 'none'
						
		return large_emails

	def opt_in_already(self, login):
		ldap = psuldap('/vol/certs')
		ldap_host = self.prop.getProperty('ldap.read.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)
				
		ldap.connect( ldap_host, ldap_login, ldap_password)
		res = ldap.search( searchfilter = 'uid=' + login, attrlist = ['mailHost'])
		
		for (dn, result) in res:
			if result.has_key("mailHost"):
				self.log.info('opt_in_alread() user: ' + login + ' has a mailHost ' + str(result['mailHost']))
				if "gmx.pdx.edu" in result["mailHost"]:
					self.log.info('opt_in_alread() user: ' + login + ' has a mailHost entry set to gmx.pdx.edu')
					return True
		return False

	def is_oamed(self, login):
		ldap = psuldap('/vol/certs')
		ldap_host = self.prop.getProperty('ldap.read.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		self.log.info('is_oamed(): connecting to LDAP: ' + ldap_host)
				
		attr = 'eduPersonAffiliation'
		ldap.connect( ldap_host, ldap_login, ldap_password)
		res = ldap.search( searchfilter = 'uid=' + login, attrlist = [attr])
		
		for (dn, result) in res:
			if result.has_key(attr):
				self.log.info('is_oamed() user: ' + login + ' has a ' + attr + ' of ' + str(result[attr]))
				#print('is_oamed() user: ' + login + ' has a ' + attr + ' of ' + str(result[attr]))

				for affiliation in result[attr]:
					if affiliation in ['SPONSORED', 'SERVICE']:
						self.log.info('is_oamed() user: ' + login + ' is not OAMed' )
						#print('is_oamed() user: ' + login + ' is not OAMed' )
						return False
		return True

	def get_ldap_attr(self, login, attr):
		ldap = psuldap('/vol/certs')
		ldap_host = self.prop.getProperty('ldap.read.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)
				
		ldap.connect( ldap_host, ldap_login, ldap_password)
		res = ldap.search( searchfilter = 'uid=' + login, attrlist = ['mailHost'])
		
		for (dn, result) in res:
			if result.has_key(attr):
				return str(result[attr])

		return None

	def route_to_google_null(self, login):
		self.log.info('route_to_google(): routing mail to google for user: ' + login)
		sleep(1)
		
		
	def is_allowed(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		
		# Does this user have an elligible account
		if not self.is_oamed(login):
			return False

		# Is this user explicitly denied
		deny_users = prop.getProperty('deny.users')
		if login in deny_users:
			return False

		# Is this user explicitly allowed
		allow_all = prop.getProperty('allow.all')
		if allow_all == 'False':
			allow_users = prop.getProperty('allow.users')
			if login in allow_users:
				return True
		else:
			return True
		
		return False


	# Temporary hack till Adrian sorts-out the access issues for modifying LDAP
	def route_to_google_hack(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		mc.set('gmx_done.' + login, None)
		mcq = MemcacheQueue('to_google', mc)
		mcq.add(login)
		res = mc.get('gmx_done.' + login)
		while res == None:
			res = mc.get('gmx_done.' + login)
			print 'Waiting for ' + login + ' to route to Google' 
			sleep(10)

	def route_to_google_needswork(self, login):
		self.update_mailHost(login, 'gmx.pdx.edu')
		self.update_mailRoutingAddress(login, )
		
	def route_to_google_old(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')

		self.log.info('route_to_google(): Routing mail to Google for user: ' + login)
		ldap_host = prop.getProperty('ldap.write.host')
		ldap_login = prop.getProperty('ldap.login')
		ldap_password = prop.getProperty('ldap.password')
		
		cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host + ' -D ' + ldap_login + " -w " + ldap_password

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

		syncprocess = subprocess.Popen(	shlex.split(cmd) ,stdin=subprocess.PIPE )

		syncprocess.communicate(input)

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('route_to_google(): continuing to route mail to Google for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('route_to_google(): success for user: ' + login)
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
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			self.log.error("route_to_google(): mailHost: Retrying LDAP update")
			status = self.update_mailHost(login, 'gmx.pdx.edu')
			retry_count = retry_count + 1
			
		status = self.update_mailRoutingAddress(login, 'pdx.edu')
		retry_count = 0
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			self.log.error("route_to_google(): mailRoutingAddress: Retrying LDAP update")
			status = self.update_mailRoutingAddress(login, 'pdx.edu')
			retry_count = retry_count + 1
			
	def update_mailHost(self, login, deliveryHost):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')

		self.log.info('update_mailHost(): Routing mail to psu for user: ' + login)
		ldap_host = prop.getProperty('ldap.write.host')
		ldap_login = prop.getProperty('ldap.login')
		ldap_password = prop.getProperty('ldap.password')
		
		cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host + ' -D ' + ldap_login + " -w " + ldap_password

		# Launch a Subprocess here to re-route email
		input = '''
dn: uid=%s, ou=people, dc=pdx, dc=edu
changetype: modify
replace: mailHost
mailHost: %s
''' % (login, deliveryHost)

		syncprocess = subprocess.Popen(	shlex.split(cmd), stdin=subprocess.PIPE )

		syncprocess.communicate(input)

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('update_mailHost(): continuing to route mail to psu for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('update_mailHost(): success for user: ' + login)
			return True
		else:
			self.log.info('update_mailHost(): failed for user: ' + login)
			return False

	def update_mailRoutingAddress(self, login, deliveryAddr):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')

		self.log.info('update_mailRoutingAddress(): Updating mailRoutingAddress for user: ' + login)
		ldap_host = prop.getProperty('ldap.write.host')
		ldap_login = prop.getProperty('ldap.login')
		ldap_password = prop.getProperty('ldap.password')
		
		cmd = '/usr/bin/ldapmodify -x -h ' + ldap_host + ' -D ' + ldap_login + " -w " + ldap_password

		# Launch a Subprocess here to re-route email
		input = '''
dn: uid=%s, ou=people, dc=pdx, dc=edu
changetype: modify
replace: mailRoutingAddress
mailRoutingAddress: %s@%s
''' % (login, login, deliveryAddr)

		syncprocess = subprocess.Popen(	shlex.split(cmd) ,stdin=subprocess.PIPE )

		syncprocess.communicate(input)

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('update_mailRoutingAddress(): Continuing to update mailRoutingAddress for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('update_mailRoutingAddress(): success for user: ' + login)
			return True
		else:
			self.log.info('update_mailRoutingAddress(): failed for user: ' + login)
			return False
			
	# Temporary hack till Adrian sorts-out the access issues for modifying LDAP
	def route_to_psu_hack(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		mc.set('psu_done.' + login, None)
		mcq = MemcacheQueue('to_psu', mc)
		mcq.add(login)
		res = mc.get('psu_done.' + login)
		while res == None:
			res = mc.get('psu_done.' + login)
			print 'Waiting for ' + login + ' to route to PSU' 
			sleep(10)
		
	def route_to_google_future(self, login):
		self.log.info('route_to_google(): routing mail to google for user: ' + login)
		ldap = psuldap('/vol/certs')
		# ldapsearch -x -h ldap.oit.pdx.edu -b 'dc=pdx, dc=edu' uid=dennis mailhost
		ldap_host = self.prop.getProperty('ldap.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		#self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)
		ldap.connect( ldap_host, ldap_login, ldap_password)
		
		dn = 'uid=' + login + ',ou=people,dc=pdx,dc=edu'
		ldap.mod_attribute(dn, 'mailHost', 'gmx.pdx.edu')		

	def route_to_psu_future(self, login):
		ldap = psuldap('/vol/certs')
		# ldapsearch -x -h ldap.oit.pdx.edu -b 'dc=pdx, dc=edu' uid=dennis mailhost
		ldap_host = self.prop.getProperty('ldap.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		#self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)
		ldap.connect( ldap_host, ldap_login, ldap_password)
		
		dn = 'uid=' + login + ',ou=people,dc=pdx,dc=edu'
		ldap.mod_attribute(dn, 'mailHost', 'cyrus.psumail.pdx.edu')		

	def get_user(self, meta):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		
		login = None
		if self.META_IDENTITY in meta:
			key = meta[self.META_IDENTITY]
			login = mc.get(key)
		else:
			self.log.info('psusys.PSUSys.get_user(), failed to find: ' + self.META_IDENTITY + ' in META')
		
		if login == None:
			login = 'dennis'
			self.log.info('psusys.PSUSys.get_user(), defaulting to user ' + login )
		else:
			self.log.info('psusys.PSUSys.get_user(), found user ' + login + ' in memcache')
		return login

	def set_user(self, login, meta):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		
		if self.META_IDENTITY in meta:
			key = meta[self.META_IDENTITY]
			mc.set(key, login)
			self.log.info('psusys.PSUSys.set_user(), set user ' + login + ' in memcache')
		else:
			self.log.info('psusys.PSUSys.set_user(), failed to find: ' + self.META_IDENTITY + ' in META')
		
	def send_conversion_email_null(self, login):
		addr = login + '@pdx.edu'
		self.log.info('send_conversion_email(): sending mail to user: ' + addr)
		sleep(1)
		# Send the conversion confirmation email to the user
		# Launch a Subprocess here to send email

	def send_conversion_email_in_progress(self, login):
		self.log.info('send_conversion_email_in_progress(): sending mail to user: ' + login)
		# Send the conversion confirmation email to the user
		# Launch a Subprocess here to send email
		cmd = '/vol/goblin/src/conversion_email_in_progress ' + login
		
		syncprocess = subprocess.Popen(	shlex.split(cmd) )

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('send_conversion_email_in_progress(): continuing to send mail for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('send_conversion_email_in_progress(): success for user: ' + login)
			return True
		else:
			self.log.info('send_conversion_email_in_progress(): failed for user: ' + login)
			return False
			

	def send_conversion_email_psu(self, login):
		self.log.info('send_conversion_email_psu(): sending mail to user: ' + login)
		# Send the conversion confirmation email to the user
		# Launch a Subprocess here to send email
		cmd = '/vol/goblin/src/conversion_email_psu ' + login
		
		syncprocess = subprocess.Popen(	shlex.split(cmd) )

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('send_conversion_email_psu(): continuing to send mail for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('send_conversion_email_psu(): success for user: ' + login)
			return True
		else:
			self.log.info('send_conversion_email_psu(): failed for user: ' + login)
			return False
			
	def send_conversion_email_google(self, login):
		self.log.info('send_conversion_email_google(): sending mail to user: ' + login)
		# Send the conversion confirmation email to the user
		# Launch a Subprocess here to send email
		cmd = '/vol/goblin/src/conversion_email_google ' + login
		
		syncprocess = subprocess.Popen(	shlex.split(cmd) )

		while (syncprocess.poll() == None):
			sleep(3)
			self.log.info('send_conversion_email_google(): continuing to send mail for user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('send_conversion_email_google(): success for user: ' + login)
			return True
		else:
			self.log.info('send_conversion_email_google(): failed for user: ' + login)
			return False
			

	def enable_gmail_null(self, login):
		self.log.info('enable_gail(): Enabling gmail for user: ' + login)
		# Enable gmail here
		sleep(1)
		
	def is_gmail_enabled(self, login):
		self.log.info('is_gmail_enabled(): Checking if gmail is enabled for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')
		
		client = gdata.apps.organization.service.OrganizationService(email=email, domain=domain, password=pw)
		retry_count = 0; status = False; result = False
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			try:
				client.ProgrammaticLogin()
				customerId = client.RetrieveCustomerId()["customerId"]
				userEmail = login + '@pdx.edu'
				result = (client.RetrieveOrgUser( customerId, userEmail )['orgUnitPath'] == 'people')
				status = True
			except CaptchaRequired :
				self.log.error('is_gmail_enabled(): Captcha being requested')
				sleep(1)
			except BadAuthentication :
				self.log.error('is_gmail_enabled(): Authentication Error' )
				sleep(1)
			except Exception, e :
				self.log.error('is_gmail_enabled(): Exception occured: ' + str(e))
				sleep(1)
				# Retry if not an obvious non-retryable error
			retry_count = retry_count + 1

		return result
		
	def google_account_status(self, login):
		self.log.info('google_account_status(): Querying account status for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')

		client = gdata.apps.service.AppsService(email=email, domain=domain, password=pw)
		retry_count = 0; status = False
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			try:
				client.ProgrammaticLogin()
				userDisabled = client.RetrieveUser(login).login.suspended
				if userDisabled == 'false':
					return {"exists": True, "enabled": True}
				elif userDisabled == 'true':
					return {"exists": True, "enabled": False}

			except AppsForYourDomainException, e:
				if e.error_code == 1301:
					self.log.error('enable_google_account(): User %s does not exist' % login)
					return {"exists": False, "enabled": False}

			except( CaptchaRequired ):
				self.log.error('enable_google_account(): Captcha being requested')

			except( BadAuthentication ):
				self.log.error('enable_google_account(): Authentication Error' )

			except:
				# Retry if not an obvious non-retryable error
				sleep(1)

			retry_count = retry_count + 1

	def enable_google_account(self, login):
		self.log.info('enable_google_account(): Enabling account for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')

		client = gdata.apps.service.AppsService(email=email, domain=domain, password=pw)
		retry_count = 0; status = False
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			try:
				client.ProgrammaticLogin()
				userDisabled = client.RestoreUser(login).login.suspended
				if userDisabled == 'false':
					status = True

			except AppsForYourDomainException, e:
				if e.error_code == 1301:
					self.log.error('enable_google_account(): User %s does not exist' % login)
					status = True

			except( CaptchaRequired ):
				self.log.error('enable_google_account(): Captcha being requested')

			except( BadAuthentication ):
				self.log.error('enable_google_account(): Authentication Error' )

			except:
				# Retry if not an obvious non-retryable error
				sleep(1)

			retry_count = retry_count + 1

	def disable_google_account(self, login):
		self.log.info('disable_google_account(): Disabling account for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')

		client = gdata.apps.service.AppsService(email=email, domain=domain, password=pw)
		retry_count = 0; status = False
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			try:
				client.ProgrammaticLogin()
				userDisabled = client.SuspendUser(login).login.suspended
				if userDisabled == 'true':
					status = True

			except AppsForYourDomainException, e:
				if e.error_code == 1301:
					self.log.error('disable_google_account(): User %s does not exist' % login)
					status = True

			except( CaptchaRequired ):
				self.log.error('disable_google_account(): Captcha being requested')

			except( BadAuthentication ):
				self.log.error('disable_google_account(): Authentication Error' )

			except:
				# Retry if not an obvious non-retryable error
				sleep(1)

			retry_count = retry_count + 1

	def enable_gmail(self, login):
		retry_count = 0; status = False
		
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			self.gmail_set_active(login)
			if self.is_gmail_enabled(login):
				status = True
			retry_count = retry_count + 1

	def gmail_set_active(self, login):
		self.log.info('enable_gmail(): Enabling gmail for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')
		
		client = gdata.apps.organization.service.OrganizationService(email=email, domain=domain, password=pw)
		retry_count = 0; status = False
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			try:
				client.ProgrammaticLogin()
				customerId = client.RetrieveCustomerId()["customerId"]
				userEmail = login + '@pdx.edu'
				client.UpdateOrgUser( customerId, userEmail, 'people')
				status = True
			except CaptchaRequired :
				self.log.error('gmail_set_active(): Captcha being requested')
				sleep(1)
			except BadAuthentication :
				self.log.error('gmail_set_active(): Authentication Error' )
				sleep(1)
			except Exception, e :
				self.log.error('gmail_set_active(): Exception occured: ' + str(e))
				sleep(1)
				# Retry if not an obvious non-retryable error
			retry_count = retry_count + 1
		return status
		
	def disable_gmail(self, login):
		self.log.info('disable_gmail(): Disabling gmail for user: ' + login)
		email = self.prop.getProperty('google.email')
		domain = self.prop.getProperty('google.domain')
		pw = self.prop.getProperty('google.password')
		
		client = gdata.apps.organization.service.OrganizationService(email=email, domain=domain, password=pw)
		client.ProgrammaticLogin()
		customerId = client.RetrieveCustomerId()["customerId"]
		userEmail = login + '@pdx.edu'
		client.UpdateOrgUser( customerId, userEmail, '/')
		
	def sync_email_null(self, login):
		self.log.info('sync_email(): syncing user: ' + login)
		sleep(1)

	def sync_email(self, login, extra_opts = ''):
		self.log.info('sync_email(): syncing user: ' + login)
		imap_host = self.prop.getProperty('imap.host')
		imap_login = self.prop.getProperty('imap.login')
				
		imapsync_dir = "/vol/google-imap/"
		imapsync_cmd = imapsync_dir + "imapsync"
		cyrus_pf = imapsync_dir + "cyrus.pf"
		google_pf = imapsync_dir + "google-prod.pf"
		
		exclude_list = "'^Shared Folders|^mail/|^Junk$|^junk$|^JUNK$|^Spam$|^spam$|^SPAM$'"
		whitespace_cleanup = " --regextrans2 's/[ ]+/ /g' --regextrans2 's/\s+$//g' --regextrans2 's/\s+(?=\/)//g' --regextrans2 's/^\s+//g' --regextrans2 's/(?=\/)\s+//g'"
		#folder_cases = " --regextrans2 's/^drafts$/[Gmail]\/Drafts/i' --regextrans2 's/^trash$/[Gmail]\/Trash/i' --regextrans2 's/^(sent|sent-mail)$/[Gmail]\/Sent Mail/i'"
		folder_cases = " --regextrans2 's/^drafts$/[Gmail]\/Drafts/i' --regextrans2 's/^trash$/[Gmail]\/Trash/i' --regextrans2 's/^(sent|sent-mail)$/[Gmail]\/Sent Mail/i'"
		command = imapsync_cmd + " --pidfile /tmp/imapsync-" + login + ".pid --host1 " + imap_host + " --port1 993 --user1 " + login + " --authuser1 " + imap_login + " --passfile1 " + cyrus_pf + " --host2 imap.gmail.com --port2 993 --user2 " + login + "@" + 'pdx.edu' + " --passfile2 " + google_pf + " --ssl1 --ssl2 --maxsize 26214400 --authmech1 PLAIN --authmech2 XOAUTH -sep1 '/' --exclude " + exclude_list + folder_cases + whitespace_cleanup + extra_opts

		if extra_opts == '':
			log_file_name = '/tmp/imapsync-' + login + '.log'
		else:
			log_file_name = '/tmp/imapsync-' + login + '-delete.log'
			
		syncprocess = subprocess.Popen(
									shlex.split(command)
									,stdout=open(log_file_name, 'w') )
	# While the process is running, and we're under the time limit
		while (syncprocess.poll() == None):
			sleep(30)
			self.log.info('sync_email(): continuing to sync user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('sync_email(): success syncing user: ' + login)
			return True
		else:
			self.log.info('sync_email(): failed syncing user: ' + login)
			return False

	def sync_email_delete2(self, login):
		return self.sync_email(login, extra_opts = ' --delete2 --delete2folders --fast ')		

	def sync_email_delete2_obs(self, login):
		self.log.info('sync_email(): syncing user: ' + login)
		imapsync_cmd = '/vol/google-imap/imapsync'
		imap_host = self.prop.getProperty('imap.host')
		imap_login = self.prop.getProperty('imap.login')
		cyrus_pf = '/opt/google-imap/cyrus.pf'
		google_pf = '/opt/google-imap/google-prod.pf'
		
		command = imapsync_cmd + " --pidfile /tmp/imapsync-full-" + login + ".pid --host1 " + imap_host + " --port1 993 --user1 " + login + " --authuser1 " + imap_login + " --passfile1 " + cyrus_pf + " --host2 imap.gmail.com --port2 993 --user2 " + login + "@" + 'pdx.edu' + " --passfile2 " + google_pf + " --ssl1 --ssl2 --maxsize 26214400 --delete2 --delete2folders --authmech1 PLAIN --authmech2 XOAUTH -sep1 '/' --exclude '^Shared Folders' "
		log_file_name = '/tmp/imapsync-' + login + '-delete.log'
		syncprocess = subprocess.Popen(	shlex.split(command), stdout = open(log_file_name, 'w') )
									
		self.log.info('sync_email(): command: ' + command )
	# While the process is running, and we're under the time limit
		while (syncprocess.poll() == None):
			sleep(30)
			self.log.info('sync_email(): continuing to sync user: ' + login)
			
		if syncprocess.returncode == 0:
			self.log.info('sync_email(): success syncing user: ' + login)
			return True
		else:
			self.log.info('sync_email(): failed syncing user: ' + login)
			return False
			

		# Call sync here
		
	def is_processing(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		key = 'email_copy_progress.' + login
		cached_data = mc.get(key)

		if (cached_data == None):
			return False
		return True

	def is_web_suspended(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		web_suspended = prop.getProperty('web.suspended')

		if web_suspended == 'True':
			self.log.info('is_web_suspended(): user: ' + login + " visited while the opt-in web site was suspended")
			return True
			
		return False
	
	def copy_progress(self, login):	
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)

		#cache_key = "copy_progress_%s" % (request.GET['login', 'default'])
		key = 'email_copy_progress.' + login
		cached_data = mc.get(key)

		if (cached_data == None):
			cached_data = 0
		#data = simplejson.dumps(cached_data)
		data = simplejson.dumps(cached_data)
		self.log.info('PSUSys.copy_progress() called, memcache_url: ' + memcache_url + ", data: " + data + ' , login: ' + login)

		return data
		#return HttpResponse(simplejson.dumps(27))
		
	def copy_email_task(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		log = logging.getLogger('')		# Logging is occuring within celery worker here
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		psu_sys = PSUSys()

		log.info("copy_email_task(): processing user: " + login)
		key = 'email_copy_progress.' + login

		account_status = psu_sys.google_account_status(login)

		# Check to make sure the user has a Google account
		if account_status["exists"] == False:
			log.info("presync_email_task(): user does not exist in Google: " + login)
			return(True)

		# Check for LDAP mail forwarding already (double checking), if
		# already opt'd-in, then immediately return and mark as complete.

		if (psu_sys.opt_in_already(login)):
			log.info("copy_email_task(): has already completed opt-in: " + login)
			mc.set(key, 100)
			return(True)
		else:
			log.info("copy_email_task(): has not already completed opt-in: " + login)
			mc.set(key, 40)

		# We temporarily enable suspended accounts for the purposes of synchronization
		if account_status["enabled"] == False:
			log.info("presync_email_task(): temporarily enabling account: " + login)
			psu_sys.enable_google_account(login)	# Enable account if previously disabled
			mc.set(key, 45)

		# Send conversion info email to users Google account
		log.info("copy_email_task(): conversion in progress email: " + login)
		psu_sys.send_conversion_email_in_progress(login)

		# Enable Google email for the user
		# This is the last item that the user should wait for.

		psu_sys.enable_gmail(login)	
		mc.set(key, 50)
	
	
		# Synchronize email to Google (and wait)
		log.info("copy_email_task(): first pass syncing email: " + login)
		status = psu_sys.sync_email_delete2(login)
		retry_count = 0
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			log.info("copy_email_task(): Retry of first pass syncing email: " + login)
			status = psu_sys.sync_email_delete2(login)
			sleep(4 ** retry_count)
			retry_count = retry_count + 1
			
		mc.set(key, 60)

		# Switch routing of email to flow to Google
	
		log.info("copy_email_task(): Routing email to Google: " + login)
		psu_sys.route_to_google(login)
		mc.set(key, 70)

		# Final email sync
		log.info("copy_email_task(): second pass syncing email: " + login)
		status = psu_sys.sync_email(login)
		retry_count = 0
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			log.info("copy_email_task(): Retry of second pass syncing email: " + login)
			status = psu_sys.sync_email(login)
			sleep(4 ** retry_count)
			retry_count = retry_count + 1
		
		mc.set(key, 80)

		# The folowing items occur without the user waiting.
		
		# Send conversion info email to users Google account
		log.info("copy_email_task(): sending post conversion email to Google: " + login)
		psu_sys.send_conversion_email_google(login)

		# Send conversion info email to users PSU account
		log.info("copy_email_task(): sending post conversion email to PSU: " + login)
		psu_sys.send_conversion_email_psu(login)

		# If the account was disabled, well...
		if account_status["enabled"] == False:
			log.info("presync_email_task(): disabling account: " + login)
			psu_sys.disable_google_account(login)	# Enable account if previously disabled
			mc.set(key, 90)

		mc.set(key, 100)

		return(True)

	def presync_email_task(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		log = logging.getLogger('')		# Logging is occuring within celery worker here
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		psu_sys = PSUSys()

		log.info("presync_email_task(): processing user: " + login)
		optin_key = 'email_copy_progress.' + login
		key = 'email_presync_progress.' + login

		# Check to see if an opt-in task is running--if so, exit
		if mc.get(optin_key) != None:
			log.info("presync_email_task(): user currently opting-in: " + login)
			return(True)

		account_status = psu_sys.google_account_status(login)

		# Check to make sure the user has a Google account
		if account_status["exists"] == False:
			log.info("presync_email_task(): user does not exist in Google: " + login)
			return(True)

		# Check for LDAP mail forwarding already (double checking), if
		# already opt'd-in, then immediately return and mark as complete.

		if (psu_sys.opt_in_already(login)):
			log.info("presync_email_task(): has already completed opt-in: " + login)
			mc.set(key, 100)
			return(True)
		else:
			log.info("presync_email_task(): has not already completed opt-in: " + login)
			mc.set(key, 40)

		# We temporarily enable suspended accounts for the purposes of synchronization
		if account_status["enabled"] == False:
			log.info("presync_email_task(): temporarily enabling account: " + login)
			psu_sys.enable_google_account(login)	# Enable account if previously disabled
			mc.set(key, 45)

		# Enable Google email for the user
		log.info("presync_email_task(): temporarily enabling Google mail: " + login)
		psu_sys.enable_gmail(login)
		mc.set(key, 50)

		# Synchronize email to Google (and wait)
		log.info("presync_email_task(): syncing email: " + login)
		status = psu_sys.sync_email_delete2(login)
		retry_count = 0
		while (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			log.info("presync_email_task(): Retry syncing email: " + login)
			status = psu_sys.sync_email_delete2(login)
			sleep(4 ** retry_count)
			retry_count = retry_count + 1

		# Synchronization complete
		mc.set(key, 70)

		# Disable Google email
		log.info("presync_email_task(): disabling Google mail: " + login)
		psu_sys.disable_gmail(login)
		mc.set(key, 80)

		if account_status["enabled"] == False:
			log.info("presync_email_task(): disabling account: " + login)
			psu_sys.disable_google_account(login)	# Enable account if previously disabled
			mc.set(key, 90)

		# Call it good.
		mc.set(key, 100)

		return(True)
	
	def recover_copy_email_task(self, login):
		'''
		Recover from case where celery task has died unexpectantly. .. Don't do delete2
		phase.
		'''
		
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		log = logging.getLogger('')		# Logging is occuring within celery worker here
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)
		psu_sys = PSUSys()

		log.info("copy_email_task(): processing user: " + login)
		key = 'email_copy_progress.' + login

		# Check for LDAP mail forwarding already (double checking), if
		# already opt'd-in, then immediately return and mark as complete.

		if (psu_sys.opt_in_already(login)):
			log.info("copy_email_task(): has already completed opt-in: " + login)
			# mc.set(key, 100)
			#return(True)
			mc.set(key, 40)
		else:
			log.info("copy_email_task(): has not already completed opt-in: " + login)
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
		if (status == False) and (retry_count < self.MAX_RETRY_COUNT):
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
		if (status == False) and (retry_count < self.MAX_RETRY_COUNT):
			status = psu_sys.sync_email(login)
			sleep(4 ** retry_count)
			retry_count = retry_count + 1
		
		mc.set(key, 80)

		# The folowing items occur without the user waiting.
		
		# Send conversion info email to users Google account
		log.info("copy_email_task(): sending post conversion email to Google: " + login)
		psu_sys.send_conversion_email_google(login)

		# Send conversion info email to users PSU account
		log.info("copy_email_task(): sending post conversion email to PSU: " + login)
		psu_sys.send_conversion_email_psu(login)

		mc.set(key, 100)

		return(True)
