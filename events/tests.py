from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import Event


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
