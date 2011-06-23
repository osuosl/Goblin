import unittest
import logging
from psusys import PSUSys

class TestAll(unittest.TestCase):
	def setUp(self):
		#logging.config.fileConfig('/vol/goblin/etc/logging-unit.conf')
		self.psusys = PSUSys()


	def test_opt_in_already(self):
		self.assertFalse(self.psusys.opt_in_already('dennis'))
		
	def test_large_emails(self):
		emailen = self.psusys.large_emails('weekse')
		print emailen

	def test_routing(self):
		self.psusys.route_to_google('a2sj')
		self.assertTrue(self.psusys.opt_in_already('a2sj'))
		self.psusys.route_to_psu('a2sj')
		self.assertFalse(self.psusys.opt_in_already('a2sj'))

if __name__ == '__main__':
	unittest.main()		
