from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
import unittest, time, re

class Lumistu5(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.base_url = "http://test-migfe.onid.oregonstate.edu"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_lumistu5(self):
        driver = self.driver
        driver.get("http://test-migfe.onid.oregonstate.edu")
        for i in range(60):
            try:
                if re.search(r"^https://login\.oregonstate\.edu/cas/login[\s\S]service=http%3a%2f%2ftest-migfe\.onid\.oregonstate\.edu%2f$", driver.current_url): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        driver.find_element_by_id("username").clear()
        driver.find_element_by_id("username").send_keys("lumistu5")
        driver.find_element_by_id("password").clear()
        driver.find_element_by_id("password").send_keys("Bulldog55Sunroof")
        driver.find_element_by_name("submit").click()
        self.assertEqual("http://test-migfe.onid.oregonstate.edu/migrate", driver.current_url)
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Are You Ready to Transition Your ONID Mailbox to Google[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("continue_btn").click()
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Current Email Will Not Be Migrated[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("id_confirm_trans-transition").click()
        driver.find_element_by_id("continue_btn").click()
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Notice to Reset Your Forward[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*lumistu5@[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("continue_btn").click()
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Prohibited Data Notice[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("id_prohibit-accept").click()
        driver.find_element_by_id("continue_btn").click()
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Reconfigure Email Access[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("id_mobile-reconfig").click()
        driver.find_element_by_id("id_mobile-narcissism").click()
        driver.find_element_by_id("continue_btn").click()
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Final Confirm[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        # Warning: verifyTextPresent may require manual changes
        try: self.assertRegexpMatches(driver.find_element_by_css_selector("BODY").text, r"^[\s\S]*Please confirm you wish to opt in to Google Mail[\s\S]*$")
        except AssertionError as e: self.verificationErrors.append(str(e))
        driver.find_element_by_id("id_final_confirm-i_accept").click()
        driver.find_element_by_id("continue_btn").click()
        try: self.assertEqual("http://test-migfe.onid.oregonstate.edu/progress", driver.current_url)
        except AssertionError as e: self.verificationErrors.append(str(e))
        time.sleep(10)
        driver.get("http://test-migfe.onid.oregonstate.edu")
        for i in range(60):
            try:
                if "http://test-migfe.onid.oregonstate.edu/opted_in" == driver.current_url: break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
    
    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException, e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException, e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()
