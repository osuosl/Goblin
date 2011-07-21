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
		self.assertTrue(len(emailen) == 2)

	def test_routing(self):
		self.psusys.route_to_google('a2sj')
		self.assertTrue(self.psusys.opt_in_already('a2sj'))
		self.psusys.route_to_psu('a2sj')
		self.assertFalse(self.psusys.opt_in_already('a2sj'))

	def test_gmail_enable(self):
		if self.psusys.is_gmail_enabled('paul'):
			self.psusys.disable_gmail('paul')
			self.assertFalse(self.psusys.is_gmail_enabled('paul'))
		else:
			self.psusys.enable_gmail('paul')
			self.assertTrue(self.psusys.is_gmail_enabled('paul'))
			self.psusys.disable_gmail('paul')
			self.assertFalse(self.psusys.is_gmail_enabled('paul'))
			
	def test_is_oamed(self):
		self.assertFalse(self.psusys.is_oamed('a2sj'))
		self.assertTrue(self.psusys.is_oamed('staplej'))
		self.assertFalse(self.psusys.is_oamed('askclas'))
		self.assertFalse(self.psusys.is_oamed('pdx00800'))
		self.assertTrue(self.psusys.is_oamed('dennis'))
		
	def test_is_allowed(self):
		self.assertTrue(self.psusys.is_allowed('dennis'))
		self.assertFalse(self.psusys.is_allowed('pdx00800'))
		
if __name__ == '__main__':
	unittest.main()		
