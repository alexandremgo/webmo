import unittest
from time import sleep

from monitor.models import Website
from monitor.website_monitor import WebsiteMonitor
from monitor.monitor import db_init


class DumbController():
    """Necessary for the availability tests"""
    def update_alert_history(self):
        pass


class MonitoringTest(unittest.TestCase):
    """Test case on functions concerning the monitoring of websites

    Problem: launch the test with "python3 -m unittest" in the website_monitor directory
    But it creates tge db inside this directory, while the real db is located at the root of the project
    """

    def setUp(self):
        """Save a website in the db for the cuurent test and instantiate a monitor
        Executed before each test method
        """

        # As it is not the real db, it has to be initiated
        db_init()
        # Urls that will imitate a problem with the server
        self.available_url = "https://www.google.fr"
        self.down_url = "https://www.google.fr/dsf,sdkflj"

        self.website = Website()
        self.website.url = self.available_url
        self.website.check_interval = 3
        self.website.save()

        self.monitor = WebsiteMonitor(self.website, DumbController())

    def test_url(self):
        """Dumb test"""
        self.assertEqual(self.website.url, "https://www.google.fr")

    def test_success_availability(self):
        """If this one does not work, change for a website that is not down and is fast"""
        self.monitor.run()
        sleep(self.website.check_interval + 1)
        self.monitor.stop()

        # As the current website instance is always deleted in tearDown, it should be equal to 0 or 100
        self.assertEqual(self.monitor.get_availability(2), 100)

    def test_down_alert(self):
        """Test if an alert has been triggerd after that the server shut down

        Do one check on a server that is not down (the availability is then set to 100%.
        Then one check on a server that is down. To imitate that we just change the website url to one
        that will respond nothing or an error
        Check if the availability goes below 80% (50%)
        """

        self.monitor.run()
        sleep(self.website.check_interval + 1)
        self.monitor.stop()

        self.website.url = self.down_url
        self.monitor.run()
        sleep(self.website.check_interval + 1)
        self.monitor.stop()

        # If the alert has been triggered, it is the only one in the db for the current website
        down_alert = self.monitor.get_last_alert()

        self.assertIsNotNone(down_alert)
        self.assertTrue(down_alert.availability < 80)

    def test_resumed_alert(self):
        """Going to cross the threshold of 80% slowly

        a: number of checks with a 2xx status codes (website is available)
        d: number of checks with other status codes
        100*a/(d+a) >= 80 <=> a >= 4*d
        So we need 4 times more a thant d to have an availability superior or equal to 80%
        """
        self.monitor.run()
        sleep(self.website.check_interval + 1)
        self.monitor.stop()

        self.website.url = self.down_url
        self.monitor.run()
        sleep(2*self.website.check_interval + 1)
        self.monitor.stop()

        # Try with 7 more available checks
        self.website.url = self.available_url
        self.monitor.run()
        sleep(7*self.website.check_interval + 1)
        self.monitor.stop()

        # Normally the last alert that has been triggered is to alert that the server has resumed
        resumed_alert = self.monitor.get_last_alert()
        self.assertIsNotNone(resumed_alert)
        self.assertTrue(resumed_alert.availability >= 80)

    def tearDown(self):
        """Delete the test website from the db
        Executed after each test method
        """
        self.website.delete_instance()


if __name__ == '__main__':
    unittest.main()
