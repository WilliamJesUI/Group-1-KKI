from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from events.models import Event
from events.views import get_when_label
from events.forms import detect_image_type


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


class EventDetailTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", first_name="Rina", last_name="Wulandari", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap",
            description="Bring the seeds you saved from last season.",
            what_to_bring="Seeds in labelled envelopes\n\nA reusable bag",
            location="Menteng Urban Farm",
            start_time=timezone.make_aware(datetime(2026, 11, 7, 9, 0)),
            end_time=timezone.make_aware(datetime(2026, 11, 7, 12, 0)),
            host=self.host,
        )
        self.event.attendees.add(self.guest)
        self.url = reverse("events:show_event", args=[self.event.id])

    def test_detail_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "event_detail.html")
        self.assertContains(response, "Community Seed Swap")
        self.assertContains(response, "Saturday, 7 November 2026")
        self.assertContains(response, "09:00-12:00 WIB")
        self.assertContains(response, "Bring the seeds you saved from last season.")
        self.assertContains(response, "Rina Wulandari")
        self.assertContains(response, "Hosted 1 event<")
        self.assertContains(response, "1 going")
        self.assertContains(response, ">BE</span>")
        self.assertEqual(response.context["bring_list"], ["Seeds in labelled envelopes", "A reusable bag"])

    def test_list_links_to_detail(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, f'href="{self.url}"')

    def test_unknown_event_returns_404(self):
        response = self.client.get(reverse("events:show_event", args=["00000000-0000-0000-0000-000000000000"]))
        self.assertEqual(response.status_code, 404)

    def test_no_bring_section_when_empty(self):
        self.event.what_to_bring = ""
        self.event.save()
        response = self.client.get(self.url)
        self.assertNotContains(response, "What to bring")

    def test_host_box_only_for_host(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, "You're the host")
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertNotContains(response, "You're the host")
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, "You're the host")

    def test_more_than_four_going(self):
        for i in range(6):
            self.event.attendees.add(User.objects.create_user(username=f"guest{i}", password="x"))
        response = self.client.get(self.url)
        self.assertContains(response, "7 going")
        self.assertContains(response, "+3")


class CreateEventTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rina", password="tomatoes123")
        self.url = reverse("events:create_event_ajax")
        self.data = {
            "name": "Community Seed Swap",
            "date": "2026-11-07",
            "start": "09:00",
            "end": "12:00",
            "location": "Menteng Urban Farm",
            "description": "Bring seeds to share.",
            "what_to_bring": "Seeds\nA bag",
            "cover_photo_url": "",
        }

    def test_must_be_logged_in(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Event.objects.count(), 0)

    def test_get_not_allowed(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_create_event(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertEqual(event.host, self.user)
        self.assertEqual(event.what_to_bring.splitlines(), ["Seeds", "A bag"])
        self.assertEqual(timezone.localtime(event.start_time).strftime("%Y-%m-%d %H:%M"), "2026-11-07 09:00")
        self.assertEqual(timezone.localtime(event.end_time).strftime("%H:%M"), "12:00")
        self.assertEqual(response.json()["url"], reverse("events:show_event", args=[event.id]))

    def test_end_time_is_optional(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["end"] = ""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Event.objects.get().end_time)

    def test_missing_name_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["name"] = ""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["name"][0]["message"], "Please give your event a name.")
        self.assertEqual(Event.objects.count(), 0)

    def test_end_before_start_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["end"] = "08:00"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("end", response.json()["errors"])

    def test_bad_cover_link_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["cover_photo_url"] = "javascript:alert(1)"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cover_photo_url", response.json()["errors"])

    def test_form_only_shown_when_logged_in(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertNotContains(response, 'id="host-event-modal"')
        self.assertContains(response, "Log in to host an event")
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'id="host-event-modal"')
        self.assertContains(response, 'popovertarget="host-event-modal"')


class EventCoverTest(TestCase):
    # The first bytes of every PNG file, plus some filler
    PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100

    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.cover_url = reverse("events:show_event_cover", args=[self.event.id])

    def test_uploaded_cover_is_served(self):
        self.event.cover_image = self.PNG_BYTES
        self.event.cover_image_type = "image/png"
        self.event.save()
        response = self.client.get(self.cover_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response.content, self.PNG_BYTES)

    def test_no_uploaded_cover_returns_404(self):
        response = self.client.get(self.cover_url)
        self.assertEqual(response.status_code, 404)

    def test_uploaded_cover_wins_over_link(self):
        self.event.cover_photo_url = "https://images.pexels.com/photos/7782153/pexels-photo-7782153.jpeg"
        self.event.cover_image = self.PNG_BYTES
        self.event.cover_image_type = "image/png"
        self.event.save()
        self.assertTrue(self.event.cover_src().startswith(self.cover_url + "?v="))
        for url in [reverse("events:show_events"), reverse("events:show_event", args=[self.event.id])]:
            response = self.client.get(url)
            self.assertContains(response, f'src="{self.event.cover_src()}"')
            self.assertNotContains(response, "pexels-photo-7782153")

    def test_cover_url_changes_after_save(self):
        self.event.cover_image = self.PNG_BYTES
        self.event.cover_image_type = "image/png"
        self.event.save()
        old_src = self.event.cover_src()
        # Pretend the event was saved a minute later
        Event.objects.filter(pk=self.event.pk).update(updated_at=self.event.updated_at + timedelta(minutes=1))
        self.event.refresh_from_db()
        self.assertNotEqual(self.event.cover_src(), old_src)

    def test_link_used_when_no_upload(self):
        self.event.cover_photo_url = "https://images.pexels.com/photos/7782153/pexels-photo-7782153.jpeg"
        self.event.save()
        self.assertEqual(self.event.cover_src(), self.event.cover_photo_url)
        response = self.client.get(reverse("events:show_event", args=[self.event.id]))
        self.assertContains(response, 'src="https://images.pexels.com/photos/7782153/pexels-photo-7782153.jpeg"')

    def test_no_cover_at_all(self):
        self.assertEqual(self.event.cover_src(), "")
        response = self.client.get(reverse("events:show_event", args=[self.event.id]))
        self.assertContains(response, "img/icons/image.svg")


class CoverUploadTest(TestCase):
    PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100

    def setUp(self):
        self.user = User.objects.create_user(username="rina", password="tomatoes123")
        self.client.login(username="rina", password="tomatoes123")
        self.url = reverse("events:create_event_ajax")
        self.data = {
            "name": "Community Seed Swap", "date": "2026-11-07", "start": "09:00", "end": "",
            "location": "Menteng Urban Farm", "description": "Bring seeds to share.",
        }

    def post_with_file(self, content, name="cover.png", content_type="image/png"):
        self.data["cover_upload"] = SimpleUploadedFile(name, content, content_type=content_type)
        return self.client.post(self.url, self.data)

    def test_detect_image_type(self):
        self.assertEqual(detect_image_type(b"\xff\xd8\xff\xe0rest"), "image/jpeg")
        self.assertEqual(detect_image_type(self.PNG_BYTES), "image/png")
        self.assertEqual(detect_image_type(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertIsNone(detect_image_type(b"GIF89a"))
        self.assertIsNone(detect_image_type(b"hello"))

    def test_upload_is_saved_in_database(self):
        response = self.post_with_file(self.PNG_BYTES)
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertEqual(bytes(event.cover_image), self.PNG_BYTES)
        self.assertEqual(event.cover_image_type, "image/png")

    def test_type_comes_from_file_content_not_name(self):
        # A real JPG with a .png name is saved as a JPG
        response = self.post_with_file(b"\xff\xd8\xff\xe0" + b"0" * 100, name="photo.png")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.get().cover_image_type, "image/jpeg")

    def test_too_big_is_rejected(self):
        response = self.post_with_file(self.PNG_BYTES + b"0" * (2 * 1024 * 1024))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["cover_upload"][0]["message"], "That photo is too big. Please pick one under 2 MB.")
        self.assertEqual(Event.objects.count(), 0)

    def test_renamed_text_file_is_rejected(self):
        response = self.post_with_file(b"just some text", name="sneaky.png")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["cover_upload"][0]["message"], "Please pick a JPG, PNG or WebP photo.")

    def test_gif_is_rejected(self):
        response = self.post_with_file(b"GIF89a" + b"0" * 100, name="dance.gif", content_type="image/gif")
        self.assertEqual(response.status_code, 400)
        self.assertIn("cover_upload", response.json()["errors"])

    def test_no_upload_is_fine(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.get().cover_image_type, "")

    def test_upload_and_link_together(self):
        self.data["cover_photo_url"] = "https://images.pexels.com/photos/7782153/pexels-photo-7782153.jpeg"
        response = self.post_with_file(self.PNG_BYTES)
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get()
        self.assertTrue(event.cover_src().startswith(reverse("events:show_event_cover", args=[event.id])))

    def test_upload_box_in_form(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'id="cover-drop"')
        self.assertContains(response, 'type="file" name="cover_upload"')
        self.assertContains(response, "JPG, PNG or WebP, up to 2 MB")


class EditEventTest(TestCase):
    PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100
    JPG_BYTES = b"\xff\xd8\xff\xe0" + b"1" * 100

    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.other = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="Bring seeds.", location="Menteng Urban Farm",
            start_time=timezone.make_aware(datetime(2026, 11, 7, 9, 0)),
            end_time=timezone.make_aware(datetime(2026, 11, 7, 12, 0)),
            cover_image=self.PNG_BYTES, cover_image_type="image/png",
            host=self.host,
        )
        self.url = reverse("events:edit_event_ajax", args=[self.event.id])
        self.detail_url = reverse("events:show_event", args=[self.event.id])
        self.data = {
            "name": "Big Seed Swap", "date": "2026-11-08", "start": "10:00", "end": "",
            "location": "Taman Suropati", "description": "Bring more seeds.",
        }

    def test_must_be_logged_in(self):
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 403)

    def test_only_host_can_edit(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 403)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Community Seed Swap")

    def test_get_not_allowed(self):
        self.client.login(username="rina", password="tomatoes123")
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_unknown_event_returns_404(self):
        self.client.login(username="rina", password="tomatoes123")
        url = reverse("events:edit_event_ajax", args=["00000000-0000-0000-0000-000000000000"])
        self.assertEqual(self.client.post(url, self.data).status_code, 404)

    def test_host_can_edit(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], self.detail_url)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Big Seed Swap")
        self.assertEqual(self.event.location, "Taman Suropati")
        self.assertEqual(timezone.localtime(self.event.start_time).strftime("%Y-%m-%d %H:%M"), "2026-11-08 10:00")
        self.assertIsNone(self.event.end_time)
        self.assertEqual(self.event.host, self.host)
        self.assertEqual(Event.objects.count(), 1)

    def test_errors_are_returned(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["name"] = ""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])

    def test_cover_kept_when_not_changed(self):
        self.client.login(username="rina", password="tomatoes123")
        self.client.post(self.url, self.data)
        self.event.refresh_from_db()
        self.assertEqual(bytes(self.event.cover_image), self.PNG_BYTES)

    def test_cover_replaced(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["cover_upload"] = SimpleUploadedFile("new.jpg", self.JPG_BYTES, content_type="image/jpeg")
        self.client.post(self.url, self.data)
        self.event.refresh_from_db()
        self.assertEqual(bytes(self.event.cover_image), self.JPG_BYTES)
        self.assertEqual(self.event.cover_image_type, "image/jpeg")

    def test_cover_removed(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["remove_cover"] = "True"
        self.client.post(self.url, self.data)
        self.event.refresh_from_db()
        self.assertIsNone(self.event.cover_image)
        self.assertEqual(self.event.cover_image_type, "")

    def test_edit_form_filled_in_for_host_only(self):
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, 'id="host-event-modal"')
        self.client.login(username="ben", password="tomatoes123")
        self.assertNotContains(self.client.get(self.detail_url), 'id="host-event-modal"')
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Edit event</h2>")
        self.assertContains(response, "Save changes")
        self.assertContains(response, f'action="{self.url}"')
        self.assertContains(response, 'value="Community Seed Swap"')
        self.assertContains(response, 'value="2026-11-07"')
        self.assertContains(response, 'value="09:00"')
        self.assertContains(response, 'value="12:00"')
        self.assertContains(response, "Current photo")

    def test_host_form_on_list_page_still_creates(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "Host an event</h2>")
        self.assertContains(response, f'action="{reverse("events:create_event_ajax")}"')
        self.assertContains(response, "Publish event")


class DeleteEventTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.other = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.event.attendees.add(self.other)
        self.url = reverse("events:delete_event", args=[self.event.id])
        self.detail_url = reverse("events:show_event", args=[self.event.id])

    def test_host_can_delete(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("events:show_events"))
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
        # The event is gone from the attendee's list too
        self.assertEqual(self.other.rsvped_events.count(), 0)

    def test_other_user_cannot_delete(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_visitor_cannot_delete(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_get_does_not_delete(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_unknown_event_returns_404(self):
        self.client.login(username="rina", password="tomatoes123")
        url = reverse("events:delete_event", args=["00000000-0000-0000-0000-000000000000"])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_confirm_popup_for_host_only(self):
        self.assertNotContains(self.client.get(self.detail_url), 'id="delete-event-modal"')
        self.client.login(username="ben", password="tomatoes123")
        self.assertNotContains(self.client.get(self.detail_url), 'id="delete-event-modal"')
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'Delete "Community Seed Swap"?')
        self.assertContains(response, 'popovertarget="delete-event-modal"')
        self.assertContains(response, f'action="{self.url}"')


class EventStatusTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")

    def make_event(self, start_in, end_in=None):
        now = timezone.now()
        return Event.objects.create(
            name="Herb Walk", description="-", location="Taman Suropati", host=self.host,
            start_time=now + start_in,
            end_time=now + end_in if end_in is not None else None,
        )

    def test_open_before_start(self):
        self.assertEqual(self.make_event(timedelta(hours=1), timedelta(hours=3)).status(), "open")

    def test_happening_between_start_and_end(self):
        self.assertEqual(self.make_event(timedelta(hours=-1), timedelta(hours=1)).status(), "happening")

    def test_ended_after_end(self):
        self.assertEqual(self.make_event(timedelta(hours=-3), timedelta(hours=-1)).status(), "ended")

    def test_no_end_time_ends_at_start(self):
        self.assertEqual(self.make_event(timedelta(hours=1)).status(), "open")
        self.assertEqual(self.make_event(timedelta(minutes=-1)).status(), "ended")


class RsvpTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.url = reverse("events:rsvp_event_ajax", args=[self.event.id])

    def test_must_be_logged_in(self):
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.event.attendees.count(), 0)

    def test_get_not_allowed(self):
        self.client.login(username="ben", password="tomatoes123")
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_unknown_event_returns_404(self):
        self.client.login(username="ben", password="tomatoes123")
        url = reverse("events:rsvp_event_ajax", args=["00000000-0000-0000-0000-000000000000"])
        self.assertEqual(self.client.post(url, {"going": "true"}).status_code, 404)

    def test_rsvp_and_cancel(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["going"], True)
        self.assertEqual(response.json()["going_count"], 1)
        self.assertEqual(response.json()["attendee_initials"], ["BE"])
        self.assertIn(self.guest, self.event.attendees.all())

        response = self.client.post(self.url, {"going": "false"})
        self.assertEqual(response.json()["going"], False)
        self.assertEqual(response.json()["going_count"], 0)
        self.assertNotIn(self.guest, self.event.attendees.all())

    def test_rsvp_twice_stays_going(self):
        # Like clicking RSVP in two open tabs: still going, and counted once
        self.client.login(username="ben", password="tomatoes123")
        self.client.post(self.url, {"going": "true"})
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.json()["going"], True)
        self.assertEqual(response.json()["going_count"], 1)

    def test_more_going_count(self):
        for i in range(5):
            self.event.attendees.add(User.objects.create_user(username=f"guest{i}", password="x"))
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.json()["going_count"], 6)
        self.assertEqual(len(response.json()["attendee_initials"]), 4)
        self.assertEqual(response.json()["more_going"], 2)

    def test_host_cannot_rsvp(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "You're the host, so you're already going.")
        self.assertEqual(self.event.attendees.count(), 0)

    def test_closed_while_happening(self):
        self.event.start_time = timezone.now() - timedelta(hours=1)
        self.event.end_time = timezone.now() + timedelta(hours=1)
        self.event.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "RSVPs are closed, this event has already started.")
        self.assertEqual(self.event.attendees.count(), 0)

    def test_closed_after_end(self):
        self.event.start_time = timezone.now() - timedelta(hours=3)
        self.event.end_time = timezone.now() - timedelta(hours=1)
        self.event.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, {"going": "true"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "RSVPs are closed, this event has ended.")

    def test_cannot_cancel_after_start(self):
        self.event.attendees.add(self.guest)
        self.event.start_time = timezone.now() - timedelta(minutes=5)
        self.event.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.post(self.url, {"going": "false"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(self.guest, self.event.attendees.all())
