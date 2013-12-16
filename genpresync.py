import subprocess
import sys
import getopt
import shlex
from time import sleep
import re
import random
from property import Property
from tasks import *
import pika
import logging

import argparse

logging.getLogger('pika').setLevel(logging.WARN)

class PreSync(object):
    def __init__(self, ulist, ldap=False, password=None, migrate=False):
        self.fac_to_presync = []
        self.prop = Property(key_file = 'opt-in.key', properties_file = 'opt-in.properties')
        self.deny = self.prop['deny.users']
        self.ulist = ulist
        self.password = password
        self.migrate = migrate
        if ldap:
            self.ulist = self.gen_ldap_list()

    def gen_presync_test(self):
        self.fac_to_presync = ['pittsh', ]

    def gen_ldap_list(self):
        tmp_file = '/tmp/presync'

        command = 'ldapsearch -w ' + self.password +' -x -LLL -h ldap.onid.orst.edu -D uid=onid_googlesync,ou=specials,o=orst.edu -b ou=people,o=orst.edu "(&(!(googleMailEnabled=1))(googlePreSync=1))" uid'
        syncprocess = subprocess.Popen(shlex.split(command), stdout=open(tmp_file, 'w'))
        while (syncprocess.poll() == None):
            sleep(30)

        return tmp_file

    def gen_presync(self):
        try:
            lines = self.ulist.readlines()
        except:
            fh = open(self.ulist)
            lines = fh.readlines()

        for line in lines:
            lsplit = [word.strip() for word in line.split(":")]
            length = len(lsplit)

            # If ['uid', user]
            if length == 2 and lsplit[0] == 'uid':
                self.fac_to_presync.append(lsplit[1])
            # If [user]
            elif length == 1 and lsplit[0] != '':
                self.fac_to_presync.append(lsplit[0])

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
            if self.migrate:
                sync = True
                forward = True
                fwd_email = "%s@onid.oregonstate.edu" % login
                copy_email_task.apply_async(args=[login, sync, forward, fwd_email], queue='optinpresync')
            else:
                presync_email_task.apply_async(args=[login], queue='optinpresync')

    def submit_test_task(self):
        for login in self.fac_to_presync:
            presync_email_test_task.apply_async(args=[login], queue='optinpresync')

if __name__ == '__main__':
    # Arguments for script use
    usage = "usage: genpresync [-l -p password] [-h]"
    desc = "Presync and force migration tool - With no options given, it reads from standard input"
    parser = argparse.ArgumentParser(description=desc, usage=usage)
    parser.add_argument("-l", "--ldap", dest='ldap', action='store_true', help="Presync users from ldap")
    parser.add_argument("-p", "--password", type=str, help="LDAP Password")
    parser.add_argument("-m", "--migrate", dest='migrate', action='store_true', help="copy_email_task instead of presync")
    args = parser.parse_args()

    # Handle the arguments
    if args.ldap and not args.password:
        print "LDAP requires option -p for a password\n"
        parser.print_help()
        sys.exit()

    ulist = sys.stdin

    # Properly configure PreSync()
    presync = PreSync(ulist=ulist, ldap=args.ldap, password=args.password, migrate=args.migrate)
    presync.gen_presync()
    presync.submit_task()
