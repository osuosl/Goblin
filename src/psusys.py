from imapstat import imapstat
from psuproperties import Property
import logging

class PSUSys:
	def __init__(self):
		self.MAX_MAIL_SIZE = pow(2,20) * 25
		self.log = logging.getLogger('goblin.psusys')
		
	def large_emails(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		imap_host = prop.getProperty('imap.host')
		imap_login = prop.getProperty('imap.login')
		imap_password = prop.getProperty('imap.password')
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

	def opt_in_complete(self, login):
		print 'boo'
		# ldapsearch -x -h ldap.oit.pdx.edu -b 'dc=pdx, dc=edu' uid=dennis mailhost
		
	def copy_progress(self, login):	
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		import simplejson
		import memcache	
		memcache_url = prop.getProperty('memcache.url')
		mc = memcache.Client([memcache_url], debug=0)

		#cache_key = "copy_progress_%s" % (request.GET['login', 'default'])
		key = 'email_copy_progress.' + login
		cached_data = mc.get(key)

		self.log.info('PSUSys.copy_progress() called')

		if (cached_data == None):
			cached_data = 0
		#data = simplejson.dumps(cached_data)
		data = simplejson.dumps(cached_data)

		return data
		#return HttpResponse(simplejson.dumps(27))
		