import requests
import time
from urllib.parse import urlparse
from peewee import fn

from monitor.repeated_timer import RepeatedTimer
from monitor.models import Website, Check, Alert


class WebsiteMonitor:
    """ Handle the monitoring for a given website

    - url: the website url (with http or https scheme)
    - check_interval: interval of time between each check
    - repeated_timer: the scheduler for the check jobs
    - full_resp_times: list of the full response times (when the entire content is loaded)
    - resp_times: list of the response times (just after that the response headers have been parsed)
    """

    # Schemes for the url property
    CORRECT_SCHEMES = ["http", "https"]
    # Availability threshold for alerts
    THRESHOLD = 80

    def __init__(self, website, controller):
        self.repeated_timer = None
        self.website = website
        self.controller = controller

        # Check the last alert (if it exists) of the website to see if it was down
        self.on_alert = False
        last_alert = self.get_last_alert()
        if last_alert and last_alert.availability < 80:
            self.on_alert = True

        # TODO: queue ? sql ? damn
        self.full_resp_times = []
        self.resp_times = []
        self.status_codes = []

    def run(self):
        """Start the scheduled monitoring check jobs for the website"""
        self.repeated_timer = RepeatedTimer(self.website.check_interval, self.check)

    def stop(self):
        if self.repeated_timer:
            self.repeated_timer.stop()

    def check(self):
        """Gather the information needed for the monitoring:
        - availability (if the response code is equal to 200)
        - full response time in seconds (when the content is loaded)
        - response time in seconds
        - response code
        """

        # TODO: check if check_interval is not too short
        # but normally it is just one thread, so it is just décalé ?
        # ou mettre un timeout égale à la moitié du check_interval
        try:
            # To get the entire (when the content is entirely loaded) response time
            start = time.time()
            r = requests.get(self.website.url,
                             timeout=(self.website.check_interval / 3))  # Send a GET requests with the requests library
            full_rt = time.time() - start
        except requests.exceptions.ConnectionError:  # from urllib3.exceptions.MaxRetryError:
            # The website does not exist, urllib3 tried 3 times
            return
        except requests.exceptions.ReadTimeout:
            # The request took more time than the timeout
            return

        # print(self.url + ": " + str(r.status_code) + " for " + str(r.elapsed))
        self.status_codes.append(r.status_code)

        self.full_resp_times.append(full_rt)

        # elapsed measures the time taken between sending the first byte of the request
        # and finishing parsing the headers
        self.resp_times.append(r.elapsed.total_seconds())

        # Create a new Check associated to the current Website
        Check.create(website=self.website, date=start, full_resp_time=full_rt,
                     resp_time=r.elapsed.total_seconds(), status_code=r.status_code)

        # Check the new availability
        self.check_availability()

    def check_availability(self):
        availability = self.get_availability(2)

        if not self.on_alert and availability < WebsiteMonitor.THRESHOLD:
            self.on_alert = True
            Alert.create(website=self.website, date=time.time(), availability=availability)
            self.controller.update_alert_history()

        elif self.on_alert and availability >= WebsiteMonitor.THRESHOLD:
            self.on_alert = False
            Alert.create(website=self.website, date=time.time(), availability=availability)
            self.controller.update_alert_history()

    def get_availability(self, timeframe=2):
        """Return the availability for the website
        It is calculated by checking the number of status codes that are 2xx
        Used by check_availability and the tests

        Parameter: timeframe (in min)
        Return: availability over the timeframe {timeframe} in percentage

        """

        min_date = time.time() - timeframe * 60

        # Take only the success status codes
        nb_2xx_codes = Check.select(fn.Count(Check.status_code)).where(Check.website == self.website,
                                                                       Check.status_code >= 200,
                                                                       Check.status_code <= 299,
                                                                       Check.date >= min_date).scalar()
        # Take all the status codes
        nb_codes = Check.select(fn.Count(Check.status_code)).where(Check.website == self.website,
                                                                   Check.date >= min_date).scalar()

        # TODO: HERE code counting ?

        return 100 * nb_2xx_codes // nb_codes if nb_codes > 0 else 0

    def get_codes_stats(self, timeframe=10):
        """Return the number of each found status codes and the availability for the website

        Parameter: timeframe (in min)
        """

        min_date = time.time() - timeframe * 60
        codes_count = {}
        nb_2xx_codes = 0
        nb_codes = 0

        query = Check.select().where(Check.website == self.website,
                                                      Check.date >= min_date)
        if query.exists():
            for check in query:
                code = check.status_code
                if code not in codes_count:
                    codes_count[code] = 1
                else:
                    codes_count[code] += 1

                if 200 <= code <= 299:
                    nb_2xx_codes += 1
                nb_codes += 1

        # Availability over the timeframe {timeframe} in percentage
        availability = 100 * nb_2xx_codes // nb_codes if nb_codes > 0 else 0

        return codes_count, availability

    def get_stats(self, timeframe=10):
        """Gather the stats of the website over the timeframe {timeframe}

        parameter: timeframe (in min): the timeframe of each stat
        return: dict of stats
        """
        # for check in Check.select().where(Check.website == self._website).order_by(Check.date.desc()):
        #     print(check.date.strftime("%A %d %B %Y %H:%M:%S") + " : " + str(check.status_code) +
        #           " in " + str(check.full_resp_time) + " s")

        min_date = time.time() - timeframe * 60

        (max_rt, avg_rt, max_full_rt, avg_full_rt) = Check.select(
            fn.Max(Check.resp_time), fn.Avg(Check.resp_time), fn.Max(Check.full_resp_time), fn.Avg(Check.full_resp_time)
        ).where(Check.website == self.website, Check.date >= min_date).scalar(as_tuple=True)

        codes_count, availability = self.get_codes_stats(timeframe)

        return {"max_rt": max_rt, "avg_rt": avg_rt, "max_full_rt": max_full_rt, "avg_full_rt": avg_full_rt,
                "availability": availability, "codes_count": codes_count}

    def get_last_alert(self):
        last_alert = None
        try:
            last_alert = Alert.select().where(Alert.website == self.website).order_by(Alert.date.desc()).get()
        except Alert.DoesNotExist:
            pass

        return last_alert
