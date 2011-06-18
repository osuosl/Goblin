from imapstat import imapstat
from psuproperties import Property

class PSUSys:
	def __init__(self):
		self.MAX_MAIL_SIZE = pow(2,20) * 25
		
	def large_emails(self, login):
		prop = Property( key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		imap_host = prop.getProperty('imap.host')
		imap_login = prop.getProperty('imap.login')
		imap_password = prop.getProperty('imap.password')
		
		ims = imapstat( imap_host, imap_login, imap_password )
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