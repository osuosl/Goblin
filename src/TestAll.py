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
		self.psusys.route_to_google('dennis')
		self.assertTrue(self.psusys.opt_in_already('dennis'))
		self.psusys.route_to_psu('dennis')
		self.assertFalse(self.psusys.opt_in_already('dennis'))

if __name__ == '__main__':
	unittest.main()		
