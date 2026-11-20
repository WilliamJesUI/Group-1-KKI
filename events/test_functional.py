"""Functional tests: a real Chrome window clicks through the Events pages, like a person would.

The unit tests in tests.py only check the HTML and JSON that Django sends. These also run our JavaScript
(event_rsvp.js, event_filters.js), so they catch things like "the button works but the page doesn't update".

They need Google Chrome on your computer (Selenium finds the matching driver by itself).
Without Chrome or Selenium they are skipped, so `python manage.py test` still works everywhere.
Run only these with: python manage.py test events.test_functional
"""
from datetime import timedelta
from unittest import SkipTest

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from events.models import Event

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    webdriver = None


class EventsInBrowserTest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # StaticLiveServerTestCase starts a real server (with our static JS files) on a free port
        super().setUpClass()
        if webdriver is None:
            super().tearDownClass()
            raise SkipTest("Selenium is not installed")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")  # no window pops up
        try:
            cls.browser = webdriver.Chrome(options=options)
        except WebDriverException:
            super().tearDownClass()
            raise SkipTest("Chrome is not installed")

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        User.objects.create_user(username="ben", password="tomatoes123")
        start = timezone.now() + timedelta(days=3)
        self.swap = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm", start_time=start, host=self.host,
        )
        Event.objects.create(
            name="Compost Workshop", description="-", location="Kemang", start_time=start, host=self.host,
        )

    def wait_for(self, condition):
        return WebDriverWait(self.browser, 5).until(condition)

    def log_in(self, username):
        self.browser.get(self.live_server_url + "/login/")
        self.browser.find_element(By.NAME, "username").send_keys(username)
        self.browser.find_element(By.NAME, "password").send_keys("tomatoes123")
        self.browser.find_element(By.CSS_SELECTOR, "form button[type=submit]").click()
        self.wait_for(EC.url_changes(self.live_server_url + "/login/"))

    def mark_page(self):
        # A flag on this page. If the page reloads, the flag is gone, so we can tell AJAX from a reload.
        self.browser.execute_script("window.stillSamePage = true;")

    def is_same_page(self):
        return self.browser.execute_script("return window.stillSamePage === true;")

    def test_rsvp_updates_the_page_without_reloading(self):
        self.log_in("ben")
        self.browser.get(f"{self.live_server_url}/events/{self.swap.id}/")
        self.mark_page()

        button = self.browser.find_element(By.CSS_SELECTOR, "[data-rsvp-url]")
        button.click()
        self.wait_for(lambda browser: button.get_attribute("aria-pressed") == "true")

        count = self.browser.find_element(By.CSS_SELECTOR, f'[data-going-count="{self.swap.id}"]')
        self.assertEqual(count.text, "1")
        avatars = self.browser.find_element(By.CSS_SELECTOR, f'[data-attendee-avatars="{self.swap.id}"]')
        self.assertEqual(avatars.text, "B")
        self.wait_for(EC.text_to_be_present_in_element((By.ID, "toast-area"), "You're going"))
        self.assertTrue(self.is_same_page())
        self.assertTrue(self.swap.attendees.filter(username="ben").exists())

    def test_search_filters_cards_without_reloading(self):
        self.browser.get(self.live_server_url + "/events/")
        self.mark_page()

        self.browser.find_element(By.ID, "event-search").send_keys("compost")
        cards = self.browser.find_element(By.ID, "event-cards")
        self.wait_for(lambda browser: "Community Seed Swap" not in cards.text)

        self.assertIn("Compost Workshop", cards.text)
        self.assertIn("q=compost", self.browser.current_url)
        self.assertTrue(self.is_same_page())
