from imapstat import imapstat
from psuproperties import Property
import logging
import simplejson
import memcache
from psuldap import psuldap
from time import sleep
import shlex, subprocess

class PSUSys:
	def __init__(self):
		self.MAX_MAIL_SIZE = pow(2,20) * 25
		self.prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		self.log = logging.getLogger('goblin.psusys')
		self.META_IDENTITY = 'REMOTE_ADDR'
		
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
					large_email[key] = msg[key]
		return large_emails

	def opt_in_already(self, login):
		ldap = psuldap('/vol/certs')
		ldap_host = self.prop.getProperty('ldap.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		self.log.info('opt_in_alread(): connecting to LDAP: ' + ldap_host)
				
		ldap.connect( ldap_host, ldap_login, ldap_password)
		res = ldap.search( searchfilter = 'uid=' + login, attrlist = ['mailHost'])
		
		for (dn, result) in res:
			if result.has_key("mailHost"):
				if result["mailHost"] == "gmx.pdx.edu":
					self.log.info('opt_in_alread() user: ' + login + ' has a mailHost entry set to gmx.pdx.edu')
					return True
		return False

	def route_to_google_null(self, login):
		self.log.info('route_to_google(): routing mail to google for user: ' + login)
		sleep(1)
		
	def route_to_google(self, login):
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

	def route_to_psu(self, login):
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

	def send_conversion_email(self, login):
		addr = login + '@pdx.edu'
		self.log.info('send_conversion_email(): sending mail to user: ' + addr)
		# Send the conversion confirmation email to the user
		# Launch a Subprocess here to send email

	def enable_gmail_null(self, login):
		self.log.info('enable_gail(): Enabling gmail for user: ' + login)
		# Enable gmail here
		sleep(1)
		
	def enable_gmail(self, login):
		self.log.info('enable_gail(): Enabling gmail for user: ' + login)
		# Enable gmail here
		
	def sync_email_null(self, login):
		self.log.info('sync_email(): syncing user: ' + login)
		sleep(1)

	def sync_email(self, login):
		self.log.info('sync_email(): syncing user: ' + login)
		imapsync_cmd = '/vol/google-imap/imapsync'
		imap_host = self.prop.getProperty('imap.host')
		imap_login = self.prop.getProperty('imap.login')
		cyrus_pf = '/opt/google-imap/cyrus.pf'
		google_pf = '/opt/google-imap/google-prod.pf'
		
		command = imapsync_cmd + " --pidfile /tmp/imapsync-full-" + login + ".pid --host1 " + imap_host + " --port1 993 --user1 " + login + " --authuser1 " + imap_login + " --passfile1 " + cyrus_pf + " --host2 imap.gmail.com --port2 993 --user2 " + login + "@" + 'pdx.edu' + " --passfile2 " + google_pf + " --ssl1 --ssl2 --maxsize 26214400 --authmech1 PLAIN --authmech2 XOAUTH -sep1 '/' --exclude '^Shared Folders' "

		syncprocess = subprocess.Popen(
									shlex.split(command)
									,stdout=subprocess.PIPE
									,stderr=subprocess.PIPE )
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
		