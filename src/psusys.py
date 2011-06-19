from imapstat import imapstat
from psuproperties import Property
import logging
import simplejson
import memcache
from psuldap import psuldap

class PSUSys:
	def __init__(self):
		self.MAX_MAIL_SIZE = pow(2,20) * 25
		self.log = logging.getLogger('goblin.psusys')
		self.prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		
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
		ldap.connect()
		print 'boo'
		# ldapsearch -x -h ldap.oit.pdx.edu -b 'dc=pdx, dc=edu' uid=dennis mailhost
		ldap_host = self.prop.getProperty('ldap.host')
		ldap_login = self.prop.getProperty('ldap.login')
		ldap_password = self.prop.getProperty('ldap.password')
		
		ldap.connect( ldap_host, ldap_login, ldap_password)
		res = ldap.search( searchfilter = 'uid=dennis', attrlist = ['mailHost'])
		mail_host = res[0][1]['mailHost'][0]
		local_mail_host = self.prop.getProperty('local.mail.host')
		if mail_host == local_mail_host:
			return False
		else:
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
		