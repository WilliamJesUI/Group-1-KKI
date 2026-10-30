from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.db import DatabaseError
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from achievements.models import ClaimedBadge, Goal, Milestone, ProgressLog
from community.models import Answer, Question
from encyclopedia.models import PlantCollection
from events.models import Event
from garden.models import PlantOfTheWeek, Post
from home import services, views
from plants.models import Plant


class LandingTestData(TestCase):
    """A small street: Siti (logged in user), Budi (a neighbor), one post, event, question and badge."""

    def setUp(self):
        self.url = reverse("home:show_landing")
        self.siti = User.objects.create_user(username="siti", password="tomatoes123", first_name="Siti")
        self.budi = User.objects.create_user(username="budi", password="tomatoes123", first_name="Budi")
        self.basil = Plant.objects.exclude(image_url="").filter(category="herbs").first()
        self.post = Post.objects.create(
            author=self.budi, caption="First basil harvest!", plant=self.basil, image_url="https://example.com/basil.jpg"
        )
        Post.objects.create(author=self.budi, caption="No photo here")
        self.event = Event.objects.create(
            name="Community Seed Swap",
            description="Bring seeds to share.",
            location="Menteng Urban Farm",
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=3),
            host=self.budi,
        )
        self.event.attendees.add(self.siti)
        self.question = Question.objects.create(author=self.siti, title="Why are my basil leaves black?")
        Answer.objects.create(question=self.question, author=self.budi, body="Too much rain.")
        self.milestone = Milestone.objects.create(
            slug="test-sprout", title="Test Sprout", description="Add a plant", metric="plants_added",
            target=1, icon="img/icons/ach-sprout.svg",
        )
        ClaimedBadge.objects.create(user=self.budi, milestone=self.milestone)


class LandingGuestTest(LandingTestData):
    def test_root_url_is_the_landing_page(self):
        self.assertEqual(self.url, "/")
        self.assertEqual(resolve("/").func, views.show_landing)

    def test_guest_sees_intro_and_log_in_register(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/landing.html")
        self.assertContains(response, "Plant together,")
        self.assertContains(response, reverse("profile:login"))
        self.assertContains(response, reverse("profile:register"))
        self.assertContains(response, "Your plot is")
        self.assertNotContains(response, "Welcome back")

    def test_no_navbar(self):
        response = self.client.get(self.url)
        self.assertTemplateNotUsed(response, "header.html")

    def test_guest_sees_every_module_preview(self):
        response = self.client.get(self.url)
        self.assertContains(response, "First basil harvest!")
        self.assertNotContains(response, "No photo here")
        self.assertContains(response, "Community Seed Swap")
        self.assertContains(response, "Why are my basil leaves black?")
        self.assertContains(response, "Test Sprout")
        self.assertContains(response, "Budi earned Test Sprout")
        self.assertContains(response, "1 of 2 gardeners")
        for slug in ["garden", "events", "encyclopedia", "community", "achievements"]:
            self.assertContains(response, f'id="spread-{slug}"')

    def test_guest_actions_send_to_log_in(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Log in to like")
        self.assertContains(response, "Log in to RSVP")

    def test_numbers_are_real(self):
        response = self.client.get(self.url)
        numbers = response.context["numbers"]
        self.assertEqual(numbers["posts"], 2)
        self.assertEqual(numbers["events"], 1)
        self.assertEqual(numbers["open_questions"], 0)
        self.assertEqual(numbers["plants"], Plant.objects.count())
        self.assertEqual(response.context["posters"], 1)
        chips = [row["chip"] for row in response.context["contents"]]
        self.assertEqual(chips[0], "2 posts")
        self.assertTrue(chips[1].startswith("Next: "))
        self.assertEqual(chips[3], "0 open questions")
        self.assertEqual(numbers["badges"], Milestone.objects.count())
        self.assertContains(response, "All 1 upcoming events")

    def test_module_links_open_for_guests(self):
        for name in ["garden:show_garden", "events:show_events", "encyclopedia:index", "community:show_questions"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class LandingLoggedInTest(LandingTestData):
    def setUp(self):
        super().setUp()
        self.client.login(username="siti", password="tomatoes123")

    def test_welcome_back(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Welcome back,")
        self.assertContains(response, "Siti. The garden")
        self.assertContains(response, "missed <em")
        self.assertContains(response, reverse("garden:show_garden"))
        self.assertNotContains(response, "Plant together,")
        self.assertNotContains(response, "Your plot is")

    def test_your_week_counts(self):
        PlantCollection.objects.create(user=self.siti).plants.add(self.basil)
        goal = Goal.objects.create(user=self.siti, title="Grow 5 chilies", plant="Chili", target=5)
        ProgressLog.objects.create(goal=goal, amount=2)
        response = self.client.get(self.url)
        mine = response.context["mine"]
        self.assertEqual(mine["new_posts"], 2)
        self.assertEqual(mine["going"], 1)
        self.assertEqual(mine["saved"], 1)
        self.assertEqual(mine["answers_for_you"], 1)
        self.assertEqual(mine["goals"][0].total_done, 2)
        chips = [row["chip"] for row in response.context["contents"]]
        self.assertEqual(chips, ["2 new this week", "Going to 1 event", "1 saved", "1 answer for you", "0 of 1 goals"])
        self.assertContains(response, "1 new event and 1 new answer on the street")
        self.assertContains(response, "Grow 5 chilies")

    def test_rsvp_shows_as_going(self):
        response = self.client.get(self.url)
        self.assertTrue(response.context["events"][0].is_going)
        self.assertContains(response, "You're going")

    def test_no_goals(self):
        response = self.client.get(self.url)
        self.assertContains(response, "No goals yet.")
        self.assertEqual(response.context["contents"][4]["chip"], "Set your first goal")


class PlantShelfTest(LandingTestData):
    def test_partial_sends_only_the_shelf(self):
        response = self.client.get(self.url, {"shelf": "herbs", "partial": "1"})
        self.assertTemplateUsed(response, "home/plant_shelf.html")
        self.assertTemplateNotUsed(response, "home/landing.html")
        self.assertTrue(response.context["shelf"])
        self.assertTrue(all(plant.category == "herbs" for plant in response.context["shelf"]))
        self.assertContains(response, 'data-shelf-pill="herbs" aria-current="true"')

    def test_unknown_pill_falls_back_to_all(self):
        response = self.client.get(self.url, {"shelf": "cactus"})
        self.assertEqual(response.context["category"], "all")

    def test_shelf_size_and_plant_of_the_week_first(self):
        PlantOfTheWeek.objects.create(plant=self.basil, short_line="Pinch it often")
        response = self.client.get(self.url)
        shelf = response.context["shelf"]
        self.assertLessEqual(len(shelf), services.SHELF_SIZE)
        self.assertEqual(shelf[0], self.basil)
        self.assertEqual(len(set(shelf)), len(shelf))
        self.assertContains(response, "Pinch it often")

    def test_plant_of_the_week_not_in_pill(self):
        PlantOfTheWeek.objects.create(plant=self.basil)
        shelf = services.plant_shelf("flowers", self.basil)
        self.assertNotIn(self.basil, shelf)

    def test_empty_pill(self):
        Plant.objects.filter(category="flowers").update(image_url="")
        response = self.client.get(self.url, {"shelf": "flowers", "partial": "1"})
        self.assertContains(response, "No plants here yet")


class EmptyAndBrokenTest(TestCase):
    def test_empty_site_still_works(self):
        Plant.objects.all().delete()
        Milestone.objects.all().delete()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for line in ["No garden posts yet", "No events coming up", "No plants here yet", "No questions yet", "No badges yet"]:
            self.assertContains(response, line)
        self.assertNotContains(response, "posted this week")

    def test_broken_table_only_hides_that_part(self):
        with mock.patch.object(services, "upcoming_events", side_effect=DatabaseError("no table")), \
                self.assertLogs("home.services", level="ERROR"):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No events coming up")
        self.assertContains(response, 'id="spread-encyclopedia"')

    def test_broken_numbers(self):
        with mock.patch.object(services, "site_numbers", side_effect=DatabaseError), self.assertLogs("home.services"):
            response = self.client.get("/")
        self.assertIsNone(response.context["numbers"])
        self.assertEqual(response.context["numbers_list"], [])
        self.assertEqual(response.context["contents"][0]["chip"], "0 posts")
        self.assertEqual(response.context["contents"][1]["chip"], "No events yet")

    def test_ago(self):
        now = timezone.now()
        self.assertEqual(services.ago(now), "just now")
        self.assertEqual(services.ago(now - timedelta(hours=2)), "2 hr ago")
        self.assertNotIn("ago", services.ago(now - timedelta(days=30)))

    def test_old_posts_still_fill_the_top(self):
        budi = User.objects.create_user(username="budi")
        post = Post.objects.create(author=budi, caption="Old one", image_url="https://example.com/a.jpg")
        Post.objects.filter(pk=post.pk).update(created_at=timezone.now() - timedelta(days=30))
        top, more = services.garden_posts(budi)
        self.assertEqual(top, post)
        self.assertEqual(more, [])
