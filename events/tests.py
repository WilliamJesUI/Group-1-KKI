from datetime import datetime, timedelta
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import constants as message_constants
from django.contrib.messages.storage.base import Message
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.template import engines
from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from events.models import Event
from events.views import get_when_label
from events.forms import EventForm, detect_image_type
from plants.models import Plant


class EventListTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="ben", password="tomatoes123")
        self.guest = User.objects.create_user(username="sasha", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap",
            description="Bring seeds to share.",
            location="Menteng Urban Farm",
            start_time=timezone.make_aware(datetime(2030, 11, 9, 9, 0)),
            end_time=timezone.make_aware(datetime(2030, 11, 9, 12, 0)),
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
        self.assertTemplateUsed(response, "event_cards.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Community Seed Swap")
        self.assertContains(response, "Menteng Urban Farm")
        self.assertContains(response, "09:00-12:00 WIB")
        self.assertContains(response, "Nov")
        self.assertContains(response, f'<span data-going-count="{self.event.id}">1</span> going')

    def test_events_tab_is_active(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, f'href="{reverse("events:show_events")}" class="nav-tab nav-tab-active">Events')

    def test_navbar_comes_from_header_html(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertTemplateUsed(response, "header.html")
        self.assertContains(response, 'id="nav-toggle"', count=1)

    def test_navbar_avatar_uses_first_name(self):
        User.objects.create_user(username="u27", first_name="Dewi", password="tomatoes123")
        self.client.login(username="u27", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        # Each user has their own random avatar color, so read it from their profile
        color = User.objects.get(username="u27").profile.avatar_bg_class
        self.assertContains(response, f'font-extrabold {color}">D</span>')
        self.assertNotContains(response, f'font-extrabold {color}">U</span>')

    def test_navbar_avatar_falls_back_to_username(self):
        # ben has no first name, so the avatar uses the username
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        color = User.objects.get(username="ben").profile.avatar_bg_class
        self.assertContains(response, f'font-extrabold {color}">B</span>')
    
    def test_navbar_shows_profile_picture_instead_of_letters(self):
        # When the user has a profile picture, the navbar shows the photo, not the letter
        ben = User.objects.get(username="ben")
        ben.profile.profile_picture = "https://example.com/ben.jpg"
        ben.profile.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'src="https://example.com/ben.jpg"')
        self.assertNotContains(response, f'font-extrabold {ben.profile.avatar_bg_class}">B</span>')

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
            start_time=timezone.make_aware(datetime(2030, 11, 9, 9, 0)),
            end_time=timezone.make_aware(datetime(2030, 11, 9, 12, 0)),
            host=self.host,
        )
        self.event.attendees.add(self.guest)
        self.url = reverse("events:show_event", args=[self.event.id])

    def test_detail_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "event_detail.html")
        self.assertContains(response, "Community Seed Swap")
        self.assertContains(response, "Saturday, 9 November 2030")
        self.assertContains(response, "09:00-12:00 WIB")
        self.assertContains(response, "Bring the seeds you saved from last season.")
        self.assertContains(response, "Rina Wulandari")
        self.assertContains(response, "Hosted 1 event<")
        self.assertContains(response, f'<span data-going-count="{self.event.id}">1</span> going')
        self.assertContains(response, ">BE</span>")
        self.assertEqual(response.context["bring_list"], ["Seeds in labelled envelopes", "A reusable bag"])
        # 1 person going: no "+N", and never a negative number
        self.assertEqual(response.context["more_going"], 0)

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
        self.assertContains(response, f'<span data-going-count="{self.event.id}">7</span> going')
        self.assertContains(response, "+3")


class CreateEventTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="rina", password="tomatoes123")
        self.url = reverse("events:create_event_ajax")
        self.data = {
            "name": "Community Seed Swap",
            "date": "2030-11-09",
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
        self.assertEqual(timezone.localtime(event.start_time).strftime("%Y-%m-%d %H:%M"), "2030-11-09 09:00")
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

    def test_create_form_starts_empty(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        form = response.context["form"]
        self.assertNotIn("date", form.initial)
        self.assertNotIn("start", form.initial)
        self.assertNotIn("end", form.initial)
        self.assertContains(response, '<input type="date" name="date" class=')

    def test_missing_date_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["date"] = ""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json()["errors"])
        self.assertEqual(Event.objects.count(), 0)

    def test_end_before_start_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["end"] = "08:00"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("end", response.json()["errors"])

    def test_end_same_as_start_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["end"] = "09:00"  # same as the start time
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["end"][0]["message"], "The end time has to be after the start time.")
        self.assertEqual(Event.objects.count(), 0)

    def test_past_date_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["date"] = "2020-05-02"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["date"][0]["message"],
            "This date and time has already passed. Please pick a later one.",
        )
        self.assertEqual(Event.objects.count(), 0)

    def test_earlier_today_shows_error(self):
        # The date alone isn't enough, the time counts too
        an_hour_ago = timezone.localtime() - timedelta(hours=1)
        self.client.login(username="rina", password="tomatoes123")
        self.data.update({"date": an_hour_ago.strftime("%Y-%m-%d"), "start": an_hour_ago.strftime("%H:%M"), "end": ""})
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json()["errors"])

    def test_year_one_shows_error_instead_of_crashing(self):
        # 05:00 on 1 Jan of year 1 in Jakarta is still year 0 in UTC, which can't be saved (it used to be a 500)
        self.client.login(username="rina", password="tomatoes123")
        self.data.update({"date": "0001-01-01", "start": "05:00", "end": ""})
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json()["errors"])

    def test_bad_cover_link_shows_error(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["cover_photo_url"] = "javascript:alert(1)"
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("cover_photo_url", response.json()["errors"])

    def test_cover_link_must_start_with_https(self):
        self.client.login(username="rina", password="tomatoes123")
        for link in ["http://images.pexels.com/photo.jpg", "ftp://example.com/photo.jpg", "images.pexels.com/photo.jpg"]:
            with self.subTest(link=link):
                self.data["cover_photo_url"] = link
                response = self.client.post(self.url, self.data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["errors"]["cover_photo_url"][0]["message"],
                    "Please paste a full image link, starting with https://",
                )
        self.assertEqual(Event.objects.count(), 0)

    def test_form_only_shown_when_logged_in(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertNotContains(response, 'id="host-event-modal"')
        self.assertContains(response, "Log in to host an event")
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'id="host-event-modal"')
        self.assertContains(response, 'popovertarget="host-event-modal"')

    def test_create_event_with_theme_plant(self):
        plant = Plant.objects.create(name="Tomato", slug="test-tomato", category="vegetables")
        self.client.login(username="rina", password="tomatoes123")
        self.data["theme_plant"] = plant.id
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Event.objects.get().theme_plant, plant)

    def test_theme_plant_is_optional(self):
        self.client.login(username="rina", password="tomatoes123")
        self.data["theme_plant"] = ""
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Event.objects.get().theme_plant)


class PlantSelectTest(TestCase):
    # The Theme plant dropdown puts each plant's photo, scientific name and category on its <option>,
    # so plant_picker.js can draw the picker from them
    def setUp(self):
        self.tomato = Plant.objects.create(
            name="Tomato",
            slug="test-tomato",
            scientific_name="Solanum lycopersicum",
            category="vegetables",
            image_url="https://bs.plantnet.org/image/o/tomato",
        )
        self.rosemary = Plant.objects.create(
            name="Rosemary", slug="test-rosemary", scientific_name="Salvia rosmarinus", category="herbs"
        )
        self.html = str(EventForm()["theme_plant"])

    def find_option(self, value):
        # The <option ...> line for one value, like '<option value="12" data-image="..." ...>Tomato</option>'
        for line in self.html.splitlines():
            if f'<option value="{value}"' in line:
                return line
        self.fail(f"No option with value {value}")

    def test_select_turns_into_picker(self):
        self.assertIn("data-plant-picker", self.html)
        self.assertIn('name="theme_plant"', self.html)

    def test_option_has_plant_data(self):
        option = self.find_option(self.tomato.id)
        # The picker asks for PlantNet's small photo (/s/), not the full size original (/o/)
        self.assertIn('data-image="https://bs.plantnet.org/image/s/tomato"', option)
        self.assertIn('data-scientific="Solanum lycopersicum"', option)
        self.assertIn('data-category="vegetables"', option)
        self.assertIn(">Tomato</option>", option)

    def test_empty_option_has_no_plant_data(self):
        option = self.find_option("")
        self.assertIn("Choose a theme plant...", option)
        self.assertNotIn("data-", option)

    def test_plant_without_photo_has_empty_image(self):
        option = self.find_option(self.rosemary.id)
        self.assertIn('data-image=""', option)
        self.assertIn('data-category="herbs"', option)

    def test_picker_script_is_on_the_page(self):
        User.objects.create_user(username="rina", password="tomatoes123")
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, "js/plant_picker.js")
        self.assertContains(response, 'data-scientific="Solanum lycopersicum"')

    def test_edit_form_starts_with_the_events_plant(self):
        host = User.objects.create_user(username="rina", password="tomatoes123")
        event = Event.objects.create(
            name="Tomato Day",
            description="All about tomatoes.",
            location="Menteng Urban Farm",
            start_time=timezone.make_aware(datetime(2030, 11, 9, 9, 0)),
            host=host,
            theme_plant=self.tomato,
        )
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(reverse("events:show_event", args=[event.id]))
        # "selected" on the Tomato option is what plant_picker.js reads to show Tomato in the field.
        # [^>]* in the pattern means "any other attributes here".
        self.assertRegex(response.content.decode(), f'<option value="{self.tomato.id}"[^>]* selected[^>]*>Tomato</option>')


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
            "name": "Community Seed Swap", "date": "2030-11-09", "start": "09:00", "end": "",
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
            start_time=timezone.make_aware(datetime(2030, 11, 9, 9, 0)),
            end_time=timezone.make_aware(datetime(2030, 11, 9, 12, 0)),
            cover_image=self.PNG_BYTES, cover_image_type="image/png",
            host=self.host,
        )
        self.url = reverse("events:edit_event_ajax", args=[self.event.id])
        self.detail_url = reverse("events:show_event", args=[self.event.id])
        self.data = {
            "name": "Big Seed Swap", "date": "2030-11-10", "start": "10:00", "end": "",
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
        self.assertEqual(timezone.localtime(self.event.start_time).strftime("%Y-%m-%d %H:%M"), "2030-11-10 10:00")
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
        self.assertContains(response, 'value="2030-11-09"')
        self.assertContains(response, 'value="09:00"')
        self.assertContains(response, 'value="12:00"')
        self.assertContains(response, "Current photo")

    def test_edit_form_end_empty_when_no_end_time(self):
        self.event.end_time = None
        self.event.save()
        self.client.login(username="rina", password="tomatoes123")
        form = self.client.get(self.detail_url).context["form"]
        self.assertEqual(form.initial["start"].strftime("%H:%M"), "09:00")
        self.assertNotIn("end", form.initial)

    def test_old_event_can_be_edited_without_changing_the_date(self):
        # The event already happened. Its saved time even has seconds (the admin's "Now" button does that),
        # but the form only has hours and minutes, so the date still counts as unchanged.
        self.event.start_time = timezone.make_aware(datetime(2020, 5, 2, 9, 0, 30))
        self.event.end_time = None
        self.event.save()
        self.client.login(username="rina", password="tomatoes123")
        self.data.update({"date": "2020-05-02", "start": "09:00", "end": ""})
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Big Seed Swap")

    def test_old_event_cannot_move_to_another_past_date(self):
        self.event.start_time = timezone.make_aware(datetime(2020, 5, 2, 9, 0))
        self.event.end_time = None
        self.event.save()
        self.client.login(username="rina", password="tomatoes123")
        self.data.update({"date": "2020-05-03", "start": "09:00", "end": ""})
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json()["errors"])
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Community Seed Swap")

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


class RsvpButtonTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.url = reverse("events:show_event", args=[self.event.id])
        self.rsvp_url = reverse("events:rsvp_event_ajax", args=[self.event.id])

    def test_button_not_going(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, f'data-rsvp-url="{self.rsvp_url}"')
        self.assertContains(response, 'aria-pressed="false"')
        self.assertContains(response, "js/event_rsvp.js")

    def test_button_going(self):
        self.event.attendees.add(self.guest)
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, 'aria-pressed="true"')
        self.assertContains(response, f'<span data-going-count="{self.event.id}">1</span> going')

    def test_host_sees_hosting_label(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, "You're hosting")
        self.assertNotContains(response, "data-rsvp-url")

    def test_visitor_sees_login_link(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Log in to RSVP")
        self.assertNotContains(response, "data-rsvp-url")

    def test_happening_now_label(self):
        self.event.start_time = timezone.now() - timedelta(hours=1)
        self.event.end_time = timezone.now() + timedelta(hours=1)
        self.event.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, "Happening now")
        self.assertNotContains(response, "data-rsvp-url")

    def test_ended_label(self):
        self.event.start_time = timezone.now() - timedelta(hours=1)
        self.event.save()
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.url)
        self.assertContains(response, "Ended")
        self.assertNotContains(response, "Happening now")
        self.assertNotContains(response, "data-rsvp-url")

    def test_page_sets_csrf_cookie(self):
        response = self.client.get(self.url)
        self.assertIn("csrftoken", response.cookies)


class RsvpCardTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.list_url = reverse("events:show_events")
        self.rsvp_url = reverse("events:rsvp_event_ajax", args=[self.event.id])

    def test_card_button_not_going(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url)
        # Once on the card and once in "Next up"
        self.assertContains(response, f'data-rsvp-url="{self.rsvp_url}"', count=2)
        self.assertContains(response, 'aria-pressed="false"', count=2)
        self.assertNotContains(response, 'aria-pressed="true"')
        self.assertContains(response, "js/event_rsvp.js")

    def test_card_button_going(self):
        self.event.attendees.add(self.guest)
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url)
        self.assertContains(response, 'aria-pressed="true"', count=2)
        self.assertContains(response, f'<span data-going-count="{self.event.id}">1</span> going', count=2)

    def test_host_sees_hosting_label_on_card(self):
        self.client.login(username="rina", password="tomatoes123")
        response = self.client.get(self.list_url)
        self.assertContains(response, "You're hosting")
        self.assertNotContains(response, "data-rsvp-url")

    def test_visitor_sees_login_link_on_card(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, "Log in to RSVP")
        self.assertNotContains(response, "data-rsvp-url")

    def test_ended_label_on_card(self):
        # Ended events aren't in Upcoming, but they stay in My events
        self.event.start_time = timezone.now() - timedelta(hours=1)
        self.event.save()
        self.event.attendees.add(self.guest)
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url + "?filter=mine")
        self.assertContains(response, "Ended")
        self.assertNotContains(response, "data-rsvp-url")

    def test_card_title_links_to_detail(self):
        response = self.client.get(self.list_url)
        detail_url = reverse("events:show_event", args=[self.event.id])
        self.assertContains(response, f'<a href="{detail_url}" class="after:absolute after:inset-0 focus-visible:outline-none">')

    def test_buttons_and_cards_have_feedback(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url)
        # Press: shrink to 0.97 in 100ms, but not for people who turned on reduced motion
        self.assertContains(response, "active:scale-[0.97] active:duration-100 motion-reduce:active:scale-100")
        # Card hover from Figma: green border and offset shadow
        self.assertContains(response, "hover:border-brand hover:shadow-[4px_4px_0_0_var(--color-ink)]")

    def test_list_sets_csrf_cookie(self):
        response = self.client.get(self.list_url)
        self.assertIn("csrftoken", response.cookies)

    def test_more_events_do_not_add_queries(self):
        # Thanks to prefetch_related, 1 event or 5 events take the same number of database queries
        self.client.login(username="ben", password="tomatoes123")
        with CaptureQueriesContext(connection) as one_event:
            self.client.get(self.list_url)
        for i in range(4):
            event = Event.objects.create(
                name=f"Herb Walk {i}", description="-", location="Taman Suropati",
                start_time=timezone.now() + timedelta(days=i + 4), host=self.host,
            )
            event.attendees.add(self.guest)
        with CaptureQueriesContext(connection) as five_events:
            self.client.get(self.list_url)
        self.assertEqual(len(five_events), len(one_event))


class EventFilterTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        now = timezone.now()
        self.past = self.make_event("Old Compost Day", now - timedelta(days=60))
        self.happening = self.make_event("Herb Walk", now - timedelta(hours=1), now + timedelta(hours=1))
        self.later = self.make_event("Seed Swap", now + timedelta(days=60))
        self.list_url = reverse("events:show_events")

    def make_event(self, name, start_time, end_time=None, host=None):
        return Event.objects.create(
            name=name, description="-", location="Menteng Urban Farm",
            start_time=start_time, end_time=end_time, host=host or self.host,
        )

    def shown_events(self, query=""):
        response = self.client.get(self.list_url + query)
        return response.context["event_list"]

    def test_upcoming_is_the_default(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.context["selected_filter"], "upcoming")
        # Exactly one pill is marked as selected
        self.assertContains(response, 'aria-current="page"', count=1)
        # Happening right now still counts as upcoming, ended events don't
        self.assertEqual(self.shown_events(), [self.happening, self.later])

    def test_upcoming_without_end_time_drops_after_start(self):
        started = self.make_event("Started Swap", timezone.now() - timedelta(minutes=5))
        self.assertNotIn(started, self.shown_events("?filter=upcoming"))

    def test_unknown_filter_falls_back_to_upcoming(self):
        response = self.client.get(self.list_url + "?filter=banana")
        self.assertEqual(response.context["selected_filter"], "upcoming")

    def test_this_month(self):
        # Middle of this month in Jakarta, so the test works on any day
        today = timezone.localdate()
        mid_month = timezone.make_aware(datetime(today.year, today.month, 15, 9, 0))
        this_month = self.make_event("Mid Month Swap", mid_month)
        events = self.shown_events("?filter=month")
        self.assertIn(this_month, events)
        self.assertNotIn(self.past, events)
        self.assertNotIn(self.later, events)

    def test_this_month_uses_jakarta_time(self):
        # 1st of this month at 03:00 Jakarta is still the previous month in UTC (20:00 the day before)
        today = timezone.localdate()
        early = self.make_event("Early Bird Swap", timezone.make_aware(datetime(today.year, today.month, 1, 3, 0)))
        self.assertIn(early, self.shown_events("?filter=month"))

    def test_my_events(self):
        self.later.attendees.add(self.guest)
        mine = self.make_event("My Own Swap", timezone.now() + timedelta(days=5), host=self.guest)
        self.client.login(username="ben", password="tomatoes123")
        # Hosted or RSVP'd, including events that already ended
        self.past.attendees.add(self.guest)
        self.assertEqual(self.shown_events("?filter=mine"), [self.past, mine, self.later])

    def test_my_events_pill_only_when_logged_in(self):
        response = self.client.get(self.list_url)
        self.assertNotContains(response, 'data-filter="mine"')
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url)
        self.assertContains(response, 'data-filter="mine"')

    def test_my_events_needs_login(self):
        self.later.attendees.add(self.guest)
        response = self.client.get(self.list_url + "?filter=mine")
        self.assertEqual(response.context["event_list"], [])
        self.assertContains(response, "Log in to see the events you host or joined.")

    def test_my_events_empty_message(self):
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url + "?filter=mine")
        self.assertContains(response, "You haven't hosted or joined any events yet.")

    def test_this_month_empty_message(self):
        Event.objects.all().delete()
        response = self.client.get(self.list_url + "?filter=month")
        self.assertContains(response, "No events found")

    def test_next_up_ignores_filter(self):
        response = self.client.get(self.list_url + "?filter=month")
        self.assertEqual(response.context["next_event"], self.later)


class EventSearchTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        later = timezone.now() + timedelta(days=5)
        self.seed_swap = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm", start_time=later, host=self.host,
        )
        self.basil = Event.objects.create(
            name="Balcony Basil 101", description="-", location="Kemang", start_time=later, host=self.host,
        )
        self.list_url = reverse("events:show_events")

    def test_search_by_name_ignores_case(self):
        response = self.client.get(self.list_url + "?q=SEED")
        self.assertEqual(response.context["event_list"], [self.seed_swap])
        self.assertEqual(response.context["query"], "SEED")

    def test_empty_search_shows_everything(self):
        response = self.client.get(self.list_url + "?q=+")
        self.assertEqual(len(response.context["event_list"]), 2)

    def test_search_works_with_filter(self):
        self.basil.start_time = timezone.now() - timedelta(days=1)
        self.basil.save()
        # Basil matches the search, but it already ended, so Upcoming leaves it out
        response = self.client.get(self.list_url + "?filter=upcoming&q=basil")
        self.assertEqual(response.context["event_list"], [])

    def test_search_box_keeps_text_and_filter(self):
        response = self.client.get(self.list_url + "?filter=month&q=seed")
        self.assertContains(response, 'name="q" value="seed"')
        self.assertContains(response, '<input type="hidden" name="filter" value="month">')
        # Switching pills keeps the search
        self.assertContains(response, 'href="?filter=upcoming&amp;q=seed"')

    def test_no_results_message(self):
        response = self.client.get(self.list_url + "?q=cactus")
        self.assertContains(response, "No events found")
        self.assertContains(response, 'No events match "cactus".')
        self.assertContains(response, "Clear search")

    def test_search_text_is_escaped(self):
        response = self.client.get(self.list_url + "?q=<b>hi</b>")
        self.assertNotContains(response, "<b>hi</b>")
        self.assertContains(response, "&lt;b&gt;hi&lt;/b&gt;")


class PartialCardsTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.guest = User.objects.create_user(username="ben", password="tomatoes123")
        later = timezone.now() + timedelta(days=5)
        self.seed_swap = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm", start_time=later, host=self.host,
        )
        self.basil = Event.objects.create(
            name="Balcony Basil 101", description="-", location="Kemang", start_time=later, host=self.host,
        )
        self.list_url = reverse("events:show_events")

    def test_partial_sends_only_the_cards(self):
        response = self.client.get(self.list_url + "?partial=1")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "event_cards.html")
        self.assertTemplateNotUsed(response, "base.html")
        self.assertNotContains(response, "<html")
        self.assertNotContains(response, "Next up")
        self.assertContains(response, "Community Seed Swap")

    def test_partial_uses_filter_and_search(self):
        response = self.client.get(self.list_url + "?filter=upcoming&q=basil&partial=1")
        self.assertEqual(response.context["event_list"], [self.basil])
        self.assertNotContains(response, "Community Seed Swap")

    def test_partial_empty_message(self):
        response = self.client.get(self.list_url + "?q=cactus&partial=1")
        self.assertContains(response, "No events found")

    def test_partial_rsvp_buttons(self):
        self.seed_swap.attendees.add(self.guest)
        self.client.login(username="ben", password="tomatoes123")
        response = self.client.get(self.list_url + "?q=seed&partial=1")
        self.assertContains(response, 'aria-pressed="true"')

    def test_partial_my_events_needs_login(self):
        response = self.client.get(self.list_url + "?filter=mine&partial=1")
        self.assertEqual(response.context["event_list"], [])
        self.assertContains(response, "Log in to see the events you host or joined.")

    def test_full_page_loads_filter_script(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, "js/event_filters.js")
        self.assertContains(response, 'id="event-filter-pills"')


class ToastTest(TestCase):
    def test_toast_area_and_script_on_page(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'id="toast-area" aria-live="polite"')
        self.assertContains(response, "js/toast.js")

    def test_messages_become_escaped_data_attributes(self):
        messages = [
            Message(message_constants.SUCCESS, 'Seed "Swap" <b>saved</b>'),
            Message(message_constants.ERROR, "Something went wrong"),
        ]
        html = render_to_string("base.html", {"messages": messages})
        # Django escapes the text, so quotes and tags can't break out of the attribute
        self.assertIn('data-toast-message="Seed &quot;Swap&quot; &lt;b&gt;saved&lt;/b&gt;" data-toast-type="success"', html)
        self.assertIn('data-toast-message="Something went wrong" data-toast-type="error"', html)

    def test_no_messages_no_toasts(self):
        response = self.client.get(reverse("events:show_events"))
        self.assertNotContains(response, "data-toast-message")

    def test_two_line_message_keeps_its_line_break(self):
        # toast.js splits the text at the first line break into a title and a message
        messages = [Message(message_constants.SUCCESS, "Event published\nYou can find it on the Events page.")]
        html = render_to_string("base.html", {"messages": messages})
        self.assertIn('data-toast-message="Event published\nYou can find it on the Events page."', html)

    def test_toast_area_comes_before_page_content(self):
        # So showToast() also works from a script inside a page's content block
        html = self.client.get(reverse("events:show_events")).content.decode()
        self.assertLess(html.index('id="toast-area"'), html.index("<main"))


class EventToastTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.client.login(username="rina", password="tomatoes123")
        self.data = {
            "name": "Community Seed Swap", "date": "2030-11-09", "start": "09:00", "end": "",
            "location": "Menteng Urban Farm", "description": "Bring seeds to share.",
        }

    def test_create_shows_toast_on_next_page(self):
        response = self.client.post(reverse("events:create_event_ajax"), self.data)
        # The fetch response is JSON, the toast waits for the page event_form.js opens next
        self.assertNotContains(response, "data-toast-message", status_code=201)
        next_page = self.client.get(response.json()["url"])
        self.assertContains(next_page, 'data-toast-message="Event published\nYou can find it on the Events page."')

    def test_edit_shows_toast(self):
        self.client.post(reverse("events:create_event_ajax"), self.data)
        event = Event.objects.get()
        self.client.get(reverse("events:show_event", args=[event.id]))  # uses up the "Event published" toast
        response = self.client.post(reverse("events:edit_event_ajax", args=[event.id]), self.data)
        next_page = self.client.get(response.json()["url"])
        self.assertContains(next_page, 'data-toast-message="Event updated\nYour changes are saved."')
        self.assertNotContains(next_page, "Event published")

    def test_delete_shows_toast(self):
        event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        response = self.client.post(reverse("events:delete_event", args=[event.id]), follow=True)
        # Django escapes the apostrophe in "It's" inside the attribute
        self.assertContains(response, 'data-toast-message="Event deleted\nIt&#x27;s off the Events page now."')

    def test_toast_shows_only_once(self):
        response = self.client.post(reverse("events:create_event_ajax"), self.data)
        self.client.get(response.json()["url"])
        again = self.client.get(response.json()["url"])
        self.assertNotContains(again, "data-toast-message")

    def test_failed_create_has_no_toast(self):
        self.data["name"] = ""
        self.client.post(reverse("events:create_event_ajax"), self.data)
        self.assertNotContains(self.client.get(reverse("events:show_events")), "data-toast-message")

    def test_rsvp_script_uses_toast(self):
        # The RSVP toast is shown by event_rsvp.js, which needs toast.js on the page first
        response = self.client.get(reverse("events:show_events"))
        html = response.content.decode()
        self.assertLess(html.index("js/toast.js"), html.index("js/event_rsvp.js"))


class CardFadeTest(TestCase):
    def test_cards_wait_40ms_more_each_up_to_360ms(self):
        host = User.objects.create_user(username="rina", password="tomatoes123")
        for i in range(11):
            Event.objects.create(
                name=f"Seed Swap {i}", description="-", location="Menteng Urban Farm",
                start_time=timezone.now() + timedelta(days=i + 1), host=host,
            )
        response = self.client.get(reverse("events:show_events"))
        self.assertContains(response, 'style="--stagger: 0ms"', count=1)
        self.assertContains(response, 'style="--stagger: 40ms"', count=1)
        self.assertContains(response, 'style="--stagger: 320ms"', count=1)
        # Cards 10 and 11 don't wait any longer than 360ms
        self.assertContains(response, 'style="--stagger: 360ms"', count=2)
        self.assertNotContains(response, "--stagger: 400ms")


class PwsCsrfTest(TestCase):
    def test_post_from_pws_passes_csrf_check(self):
        # On PWS the browser sends Origin: https://..., but Django only sees plain http behind PWS.
        # CSRF_TRUSTED_ORIGINS in settings.py is what lets these POSTs through instead of a 403.
        host = "william-jesiel-growyourgarden.pws.cs.ui.ac.id"
        User.objects.create_user(username="rina", password="tomatoes123")
        client = Client(enforce_csrf_checks=True)  # the normal test client skips CSRF checks, this one doesn't
        client.login(username="rina", password="tomatoes123")
        page = client.get(reverse("events:show_events"), HTTP_HOST=host)
        token = page.cookies["csrftoken"].value
        response = client.post(
            reverse("events:create_event_ajax"), {},
            HTTP_HOST=host, HTTP_ORIGIN=f"https://{host}", HTTP_X_CSRFTOKEN=token,
        )
        # 400 means the view checked the (empty) form, so the CSRF check let the POST through.
        # A blocked POST would be a 403.
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])


class CardAvatarTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        self.event = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=3), host=self.host,
        )
        self.list_url = reverse("events:show_events")

    def add_people(self, names):
        # Each name becomes a user who RSVP'd, created in this order (so their ids go up in this order)
        for name in names:
            first, last = name.split()
            person = User.objects.create_user(username=first.lower(), first_name=first, last_name=last, password="tomatoes123")
            self.event.attendees.add(person)

    def card(self, response):
        return [event for event in response.context["event_list"] if event == self.event][0]

    def test_nobody_going_shows_text(self):
        response = self.client.get(self.list_url)
        self.assertEqual(self.card(response).card_initials, [])
        # "0 going" is visible (not sr-only), and there are no avatars
        self.assertContains(response, f'<p data-going-label="{self.event.id}" class="flex items-center gap-2 text-[13px] font-extrabold">')
        self.assertNotContains(response, '<span class="card-avatar')

    def test_one_person_one_avatar(self):
        self.add_people(["Sari Kusuma"])
        response = self.client.get(self.list_url)
        self.assertContains(response, '<span class="card-avatar card-avatar-lilac">SK</span>')
        self.assertNotContains(response, '<span class="card-avatar card-avatar-more">')

    def test_two_avatars_then_plus_the_rest(self):
        # Like Figma: 2 initials (lilac, pink), then a green "+N" for everyone else
        self.add_people(["Sari Kusuma", "Budi Hartono", "Citra Dewi", "Dimas Putra", "Eka Lestari"])
        response = self.client.get(self.list_url)
        self.assertContains(response, '<span class="card-avatar card-avatar-lilac">SK</span>')
        self.assertContains(response, '<span class="card-avatar card-avatar-pink">BH</span>')
        self.assertContains(response, '<span class="card-avatar card-avatar-more">+3</span>')
        self.assertNotContains(response, ">CD</span>")
        # "5 going" is still on the card for screen readers
        self.assertContains(response, f'<p data-going-label="{self.event.id}" class="flex items-center gap-2 text-[13px] font-extrabold sr-only">')
        self.assertContains(response, f'<span data-going-count="{self.event.id}">5</span> going')

    def test_rsvp_answer_uses_the_same_people_as_the_card(self):
        # The card and the RSVP answer both go by id, so the avatars don't jump around after an RSVP
        self.add_people(["Sari Kusuma", "Budi Hartono", "Citra Dewi"])
        User.objects.create_user(username="ben", password="tomatoes123")
        self.client.login(username="ben", password="tomatoes123")
        card_initials = self.card(self.client.get(self.list_url)).card_initials
        rsvp = self.client.post(reverse("events:rsvp_event_ajax", args=[self.event.id]), {"going": "true"})
        self.assertEqual(rsvp.json()["attendee_initials"][:2], card_initials)
        self.assertEqual(card_initials, ["SK", "BH"])

    def test_next_up_card_keeps_its_text(self):
        # Only the cards in the grid get avatars, "Next up" still says "N going"
        self.add_people(["Sari Kusuma"])
        response = self.client.get(self.list_url)
        self.assertContains(response, f'<p class="text-xs font-bold"><span data-going-count="{self.event.id}">1</span> going</p>')

    def test_avatar_styles_are_on_the_page(self):
        # event_rsvp.js draws new avatars after an RSVP, so their styles have to be on the page from the start
        response = self.client.get(self.list_url)
        self.assertContains(response, ".card-avatar {")
        self.assertContains(response, ".card-avatar-more {")


class HideNavbarTest(TestCase):
    def test_empty_header_block_hides_the_navbar(self):
        # Like a Log in page: it extends base.html but leaves the header block empty
        page = engines["django"].from_string(
            '{% extends "base.html" %}'
            "{% block header %}{% endblock header %}"
            "{% block content %}<h1>Log in</h1>{% endblock content %}"
        )
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        html = page.render({}, request)
        # The ids navbar.js looks for are gone, but the page itself and the toasts still work
        self.assertNotIn('id="nav-toggle"', html)
        self.assertNotIn('id="nav-menu"', html)
        self.assertIn("<h1>Log in</h1>", html)
        self.assertIn('id="toast-area"', html)


class ThemePlantTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username="rina", password="tomatoes123")
        later = timezone.now() + timedelta(days=5)
        self.rose = Plant.objects.create(name="Rose", slug="test-rose", category="flowers")
        # The name doesn't say "rose", so a search for rose can only find it through the theme plant
        self.pruning = Event.objects.create(
            name="Weekend Pruning", description="-", location="Kemang", start_time=later, host=self.host,
            theme_plant=self.rose,
        )
        self.seed_swap = Event.objects.create(
            name="Community Seed Swap", description="-", location="Menteng Urban Farm", start_time=later, host=self.host,
        )
        self.list_url = reverse("events:show_events")

    def test_card_tag_links_to_encyclopedia(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, 'href="/encyclopedia/test-rose/"')

    def test_no_tag_without_theme_plant(self):
        response = self.client.get(self.list_url + "?q=seed&partial=1")
        self.assertContains(response, "Community Seed Swap")
        self.assertNotContains(response, "/encyclopedia/")

    def test_search_finds_theme_plant(self):
        response = self.client.get(self.list_url + "?q=ROSE")
        self.assertEqual(response.context["event_list"], [self.pruning])

    def test_plant_filter(self):
        response = self.client.get(self.list_url + "?plant=test-rose")
        self.assertEqual(response.context["event_list"], [self.pruning])
        self.assertEqual(response.context["selected_plant"], self.rose)
        self.assertContains(response, "Showing events for")
        # The search box and the pills keep the plant
        self.assertContains(response, 'name="plant" value="test-rose"')
        self.assertContains(response, 'href="?filter=upcoming&amp;plant=test-rose"')

    def test_unknown_plant_shows_everything(self):
        response = self.client.get(self.list_url + "?plant=cactus")
        self.assertEqual(len(response.context["event_list"]), 2)
        self.assertIsNone(response.context["selected_plant"])
        self.assertNotContains(response, "Showing events for")

    def test_plant_filter_works_with_search(self):
        response = self.client.get(self.list_url + "?plant=test-rose&q=seed")
        self.assertEqual(response.context["event_list"], [])

    def test_partial_keeps_plant_filter(self):
        response = self.client.get(self.list_url + "?plant=test-rose&partial=1")
        self.assertEqual(response.context["event_list"], [self.pruning])
        self.assertNotContains(response, "Community Seed Swap")

    def test_detail_page_links(self):
        response = self.client.get(reverse("events:show_event", args=[self.pruning.id]))
        self.assertContains(response, 'href="/encyclopedia/test-rose/"')
        self.assertContains(response, self.list_url + "?plant=test-rose")
        self.assertContains(response, "More Rose events")

    def test_detail_page_without_theme_plant(self):
        response = self.client.get(reverse("events:show_event", args=[self.seed_swap.id]))
        self.assertNotContains(response, "/encyclopedia/")
        self.assertNotContains(response, "?plant=")