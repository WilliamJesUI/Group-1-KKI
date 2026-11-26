from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from events.models import Event
from plants.models import Plant


def later(days=2):
    return timezone.now() + timedelta(days=days)


def event_data(**overrides):
    data = {
        "name": "Seed Swap",
        "description": "Bring seeds, take seeds.",
        "location": "Menteng Urban Farm",
        "start_time": later().isoformat(),
    }
    data.update(overrides)
    return data


class EventAPITestCase(APITestCase):
    def setUp(self):
        self.host = User.objects.create_user("ben", password="pw-12345")
        self.other = User.objects.create_user("ala", password="pw-12345")
        self.event = Event.objects.create(
            name="Tomato Day", description="All about tomatoes", location="UI",
            start_time=later(), host=self.host,
        )
        self.list_url = reverse("events:api_event_list")
        self.detail_url = reverse("events:api_event_detail", args=[self.event.id])
        self.rsvp_url = reverse("events:api_event_rsvp", args=[self.event.id])


class EventListAPITests(EventAPITestCase):
    def test_anyone_can_list_events(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Tomato Day")
        self.assertEqual(response.data[0]["host"], "ben")

    def test_search_finds_nothing(self):
        response = self.client.get(self.list_url, {"q": "does-not-exist"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_ended_events_are_not_upcoming(self):
        Event.objects.create(
            name="Old", description="d", location="l",
            start_time=timezone.now() - timedelta(days=3), host=self.host,
        )
        names = [event["name"] for event in self.client.get(self.list_url).data]
        self.assertEqual(names, ["Tomato Day"])

    # 401 (not logged in), because TokenAuthentication comes first
    def test_guest_cannot_create(self):
        response = self.client.post(self.list_url, event_data(), format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Event.objects.count(), 1)

    def test_logged_in_user_creates_event_as_host(self):
        self.client.force_authenticate(self.other)
        plant = Plant.objects.create(name="Basil Test", slug="basil-test")
        response = self.client.post(self.list_url, event_data(theme_plant="basil-test"), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["host"], "ala")
        self.assertEqual(response.data["theme_plant_name"], "Basil Test")
        self.assertEqual(Event.objects.get(name="Seed Swap").theme_plant, plant)

    def test_host_in_the_data_is_ignored(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self.list_url, event_data(host="ben"), format="json")
        self.assertEqual(response.data["host"], "ala")

    def test_past_start_time_is_refused(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self.list_url, event_data(start_time=later(-1).isoformat()), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("start_time", response.data)

    def test_end_before_start_is_refused(self):
        self.client.force_authenticate(self.other)
        data = event_data(start_time=later(2).isoformat(), end_time=later(1).isoformat())
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("end_time", response.data)

    def test_http_cover_link_is_refused(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self.list_url, event_data(cover_photo_url="http://a.com/x.jpg"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("cover_photo_url", response.data)


class EventDetailAPITests(EventAPITestCase):
    def test_anyone_can_read_one_event(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.event.id))
        self.assertEqual(response.data["status"], "open")

    def test_missing_event_is_404(self):
        url = reverse("events:api_event_detail", args=["00000000-0000-0000-0000-000000000000"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_host_can_patch(self):
        self.client.force_authenticate(self.host)
        response = self.client.patch(self.detail_url, {"name": "Tomato Night"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Tomato Night")
        self.assertEqual(self.event.location, "UI")

    def test_other_user_cannot_patch(self):
        self.client.force_authenticate(self.other)
        response = self.client.patch(self.detail_url, {"name": "Hacked"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Tomato Day")

    def test_put_needs_every_required_field(self):
        self.client.force_authenticate(self.host)
        response = self.client.put(self.detail_url, {"name": "Only a name"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_other_user_cannot_delete(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_host_can_delete(self):
        self.client.force_authenticate(self.host)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 204)
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_moderator_can_delete(self):
        moderator = User.objects.create_user("mod", password="pw-12345", is_staff=True)
        self.client.force_authenticate(moderator)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 204)


class EventRSVPAPITests(EventAPITestCase):
    def test_guest_cannot_rsvp(self):
        self.assertEqual(self.client.post(self.rsvp_url, {"going": True}, format="json").status_code, 401)

    def test_rsvp_and_cancel(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(self.rsvp_url, {"going": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_going"])
        self.assertEqual(response.data["going_count"], 1)
        # Sending going=true twice doesn't undo it
        self.client.post(self.rsvp_url, {"going": True}, format="json")
        self.assertEqual(self.event.attendees.count(), 1)
        response = self.client.post(self.rsvp_url, {"going": False}, format="json")
        self.assertFalse(response.data["is_going"])
        self.assertEqual(response.data["going_count"], 0)

    def test_host_cannot_rsvp(self):
        self.client.force_authenticate(self.host)
        self.assertEqual(self.client.post(self.rsvp_url, {"going": True}, format="json").status_code, 400)

    def test_cannot_rsvp_to_ended_event(self):
        self.event.start_time = timezone.now() - timedelta(days=1)
        self.event.save()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.rsvp_url, {"going": True}, format="json").status_code, 400)

    def test_get_is_not_allowed(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.rsvp_url).status_code, 405)


class EventPlantChoicesAPITests(APITestCase):
    def test_anyone_gets_plant_slugs_and_names(self):
        Plant.objects.create(name="Basil Test", slug="basil-test")
        response = self.client.get(reverse("events:api_event_plants"))
        self.assertEqual(response.status_code, 200)
        self.assertIn({"slug": "basil-test", "name": "Basil Test"}, response.data)

class EventTokenAPITests(EventAPITestCase):
    def test_login_gives_a_token(self):
        response = self.client.post(reverse("api_token"), {"username": "ala", "password": "pw-12345"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token"], Token.objects.get(user=self.other).key)

    def test_wrong_password_gives_no_token(self):
        response = self.client.post(reverse("api_token"), {"username": "ala", "password": "nope"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_app_can_rsvp_with_a_token(self):
        token = Token.objects.create(user=self.other)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token.key)
        response = self.client.post(self.rsvp_url, {"going": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_going"])

    def test_old_token_gets_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)