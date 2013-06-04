import subprocess
import sys
import shlex
from time import sleep
import re
import random
from property import Property
from tasks import *
import pika

class PreSync():
	def __init__(self):
		self.fac_to_presync = []
		self.prop = Property(key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		self.deny = self.prop.getProperty('deny.users')
	
	def gen_presync_test(self):
		self.fac_to_presync = ['fogartym', 'bjms']

	def gen_presync(self):
		tmp_file = '/tmp/presync'
		command = 'ldapsearch -x -LLL -h ldap.onid.orst.edu -D uid=onid_googlesync,ou=specials,o=orst.edu -b ou=people,o=orst.edu "(googlePreSync=1)" uid uniqueidentifier sn givenName osuPrimaryAffiliation'
		syncprocess = subprocess.Popen(shlex.split(command), stdout=open(tmp_file, 'w'))
		while (syncprocess.poll() == None):
			sleep(30)
	
		fh = open(tmp_file)
		lines = fh.readlines()
		haveRead = False
		firstName = lastName = loginName = pidm = id = ""
		role = ''
		invalid = False
		cmd = ''
		facRe = re.compile('FAC', re.IGNORECASE)
		staffRe = re.compile('STAFF', re.IGNORECASE)
		empRe = re.compile('EMP', re.IGNORECASE)
		stuRe = re.compile('STUDENT', re.IGNORECASE)
		disabledRe = re.compile('DISABLED', re.IGNORECASE)
		terminatedRe = re.compile('TERMINATED', re.IGNORECASE)
		expiredRe = re.compile('EXPIRED', re.IGNORECASE)
		
		for line in lines:
			line = line.rstrip()
			if (line):
				try:
					(a, v) = re.split(":", line)
				except:
					break
				if (a == "uid"):
					loginName = v.lstrip()
					haveRead = True
				if (a == "sn"):
					lastName = v.lstrip()
				if (a == "givenName"):
					firstName = v.lstrip()
				if (a == 'eduPersonAffiliation'):
					if (facRe.search(v) is not None) or (staffRe.search(v) is not None)  or (empRe.search(v) is not None) and not invalid:
						role = 'Faculty'
					elif (stuRe.search(v) is not None) and (role <> 'Faculty') and not invalid: 
						role = 'Student'
					elif (disabledRe.search(v) is not None) or (terminatedRe.search(v) is not None) or (expiredRe.search(v) is not None):
						invalid = True
						role = ''
						
				if (a == "uniqueidentifier"):
					pidm = ""
					id = v.lstrip()
					if (id[0:1] == "B"):
						id = "SPONSORED_" + id
					else:
						pidm = id[1:]
			else:
				if (haveRead == True) and (id):
					if role == 'Faculty':
						if loginName not in self.deny:
							self.fac_to_presync.append(loginName)
					elif role == 'Student':
						pass
						#print 'student ' + loginName
						
					firstName = lastName = loginName = pidm = id = ""
					role = ''
					haveRead = False
					invalid = False
		random.shuffle(self.fac_to_presync)

	def get_presync_list(self):
		return self.fac_to_presync
	
	def purge_queue(self):
		rabbitmq_login = self.prop.getProperty('rabbitmq.login')
		rabbitmq_pw = self.prop.getProperty('rabbitmq.password')
		rabbitmq_host = self.prop.getProperty('rabbitmq.host')
		credentials = pika.PlainCredentials(rabbitmq_login, rabbitmq_pw)
		con = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, virtual_host=rabbitmq_login, credentials=credentials))
		c = con.channel()
		c.queue_purge( queue=rabbitmq_login)
		
	def submit_task(self):
		for login in self.fac_to_presync:
			presync_email_task.apply_async(args=[login], queue='optinpresync')

	def submit_test_task(self):
		for login in self.fac_to_presync:
			presync_email_test_task.apply_async(args=[login], queue='optinpresync')
	
if __name__ == '__main__':
	presync = PreSync()
	presync.gen_presync()
	#print presync.get_presync_list()
	presync.purge_queue()
	presync.submit_task()
