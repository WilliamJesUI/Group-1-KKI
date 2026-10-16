from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import Event
from events.views import get_when_label


class EventListTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="ben", password="tomatoes123")
        self.guest = User.objects.create_user(username="sasha", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap",
            description="Bring seeds to share.",
            location="Menteng Urban Farm",
            start_time=timezone.make_aware(datetime(2026, 11, 7, 9, 0)),
            end_time=timezone.make_aware(datetime(2026, 11, 7, 12, 0)),
            host=self.host,
        )
        self.event.attendees.add(self.guest)

    def test_event_model(self):
        self.assertEqual(str(self.event), "Community Seed Swap")
        self.assertEqual(self.event.attendees.count(), 1)
        self.assertIn(self.event, self.host.hosted_events.all())
        self.assertIn(self.event, self.guest.rsvped_events.all())

    def test_event_list_page(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "event_list.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Community Seed Swap")
        self.assertContains(response, "Menteng Urban Farm")
        self.assertContains(response, "09:00-12:00 WIB")
        self.assertContains(response, "Nov")
        self.assertContains(response, "1 going")

    def test_events_tab_is_active(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, f'href="{reverse("events:show_events")}" class="nav-tab nav-tab-active">Events')

    def test_only_start_time_when_no_end_time(self):
        self.event.end_time = None
        self.event.save()
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "09:00 WIB")
        self.assertNotContains(response, "09:00-")

    def test_only_start_time_when_end_time_is_same(self):
        self.event.end_time = self.event.start_time
        self.event.save()
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "09:00 WIB")
        self.assertNotContains(response, "09:00-")

    def test_empty_event_list_page(self):
        Event.objects.all().delete()
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "Nothing here yet")

    def test_banner_is_shown(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "Grow better,")
        self.assertContains(response, "Meet, share and grow together")

    def test_next_up_shows_soonest_upcoming_event(self):
        Event.objects.create(
            name="Past Compost Day", description="-", location="Tebet Eco Park",
            start_time=timezone.now() - timedelta(days=1), host=self.host,
        )
        soon = Event.objects.create(
            name="Tomorrow Herb Walk", description="-", location="Taman Suropati",
            start_time=timezone.now() + timedelta(days=1), host=self.host,
        )
        response = self.client.get(reverse("events:show_events"))
        self.assertEqual(response.context["next_event"], soon)
        self.assertContains(response, "Next up · Tomorrow")

    def test_no_next_up_when_no_upcoming_events(self):
        self.event.start_time = timezone.now() - timedelta(days=1)
        self.event.save()
        response = self.client.get(reverse("events:show_events"))
        self.assertIsNone(response.context["next_event"])
        self.assertNotContains(response, "Next up")


class WhenLabelTest(TestCase):
    def test_labels(self):
        now = timezone.now()
        self.assertEqual(get_when_label(now), "Today")
        self.assertEqual(get_when_label(now + timedelta(days=1)), "Tomorrow")
        in_three_days = now + timedelta(days=3)
        self.assertEqual(get_when_label(in_three_days), "This " + timezone.localtime(in_three_days).strftime("%A"))
        self.assertEqual(get_when_label(now + timedelta(days=10)), "")
