import subprocess
import sys
import shlex
from time import sleep
import re
import random
from property import Property
from tasks import *
import pika
import logging

logging.getLogger('pika').setLevel(logging.WARN)

class PreSync():
	def __init__(self):
		self.fac_to_presync = []
		self.prop = Property(key_file = 'opt-in.key', properties_file = 'opt-in.properties')
		self.deny = self.prop['deny.users']
	
	def gen_presync_test(self):
		self.fac_to_presync = ['pittsh', ]

	def gen_presync(self):
		tmp_file = '/tmp/presync'
		command = 'ldapsearch -x -LLL -h ldap.onid.orst.edu -D uid=onid_googlesync,ou=specials,o=orst.edu -b ou=people,o=orst.edu "(googlePreSync=1)" uid osuUID sn givenName osuPrimaryAffiliation'
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
						
				if (a == "osuUID"):
					pidm = ""
					id = v.lstrip()
					if (id[0:1] == "B"):
						id = "SPONSORED_" + id
					else:
						pidm = id[1:]
			else:
				if (haveRead == True) and (id):
					if loginName not in self.deny:
						self.fac_to_presync.append(loginName)
						
				firstName = lastName = loginName = pidm = id = ""
				role = ''
				haveRead = False
				invalid = False
		random.shuffle(self.fac_to_presync)

	def get_presync_list(self):
		return self.fac_to_presync
	
	def purge_queue(self):
		rabbitmq_login = self.prop['rabbitmq.login']
		rabbitmq_pw = self.prop['rabbitmq.password']
		rabbitmq_host = self.prop['rabbitmq.host']
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
