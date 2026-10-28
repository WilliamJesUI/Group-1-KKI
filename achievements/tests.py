from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from achievements.models import CheckIn, ClaimedBadge, Milestone
from achievements.services import can_claim, check_in_today, current_streak, get_metric, record_progress


class ServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")

    def test_record_progress_adds_up(self):
        record_progress(self.user, "answers_given")
        record_progress(self.user, "answers_given", 4)
        self.assertEqual(get_metric(self.user, "answers_given"), 5)

    def test_metric_is_zero_without_progress(self):
        self.assertEqual(get_metric(self.user, "answers_given"), 0)

    def test_streak_counts_days_in_a_row(self):
        today = timezone.localdate()
        for days_ago in (0, 1, 2, 4):  # day 3 is missing, so the streak stops at 3
            CheckIn.objects.create(user=self.user, date=today - timedelta(days=days_ago))
        self.assertEqual(current_streak(self.user), 3)

    def test_streak_survives_until_the_end_of_today(self):
        today = timezone.localdate()
        CheckIn.objects.create(user=self.user, date=today - timedelta(days=1))
        self.assertEqual(current_streak(self.user), 1)

    def test_streak_resets_after_a_missed_day(self):
        CheckIn.objects.create(user=self.user, date=timezone.localdate() - timedelta(days=2))
        self.assertEqual(current_streak(self.user), 0)

    def test_check_in_only_counts_once_per_day(self):
        self.assertTrue(check_in_today(self.user))
        self.assertFalse(check_in_today(self.user))
        self.assertEqual(CheckIn.objects.filter(user=self.user).count(), 1)

    def test_can_claim_needs_progress_and_no_earlier_claim(self):
        milestone = Milestone.objects.get(slug="first-sprout")
        self.assertFalse(can_claim(self.user, milestone))
        record_progress(self.user, "plants_added")
        self.assertTrue(can_claim(self.user, milestone))
        ClaimedBadge.objects.create(user=self.user, milestone=milestone)
        self.assertFalse(can_claim(self.user, milestone))


class VisitorTests(TestCase):
    def test_visitor_has_no_progress_and_cannot_claim(self):
        milestone = Milestone.objects.get(slug="first-sprout")
        self.assertEqual(get_metric(AnonymousUser(), "plants_added"), 0)
        self.assertFalse(can_claim(AnonymousUser(), milestone))


class PageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.url = reverse("achievements:show_achievements")

    def test_page_loads_for_visitors_with_zero_progress(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["unlocked"], 0)
        self.assertContains(response, "Log in to track")
        self.assertNotContains(response, "Claim badge")

    def test_page_shows_a_claim_button_for_a_finished_milestone(self):
        record_progress(self.user, "plants_added")
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "Claim badge")
        # One plant finishes First Sprout and also starts Herb Garden (1 of 3), so two are in progress
        self.assertEqual(response.context["milestones_in_progress"], 2)

    def test_progress_percent_rounds_down(self):
        record_progress(self.user, "answers_given", 3)
        self.client.force_login(self.user)
        cards = self.client.get(self.url).context["cards"]
        neighbor = next(card for card in cards if card["milestone"].slug == "good-neighbor")
        self.assertEqual(neighbor["percent"], 30)

    def test_plant_filter_only_shows_that_plant(self):
        response = self.client.get(self.url + "?plant=tomato")
        slugs = [card["milestone"].slug for card in response.context["cards"]]
        self.assertEqual(slugs, ["tomato-time"])

    def test_unknown_plant_filter_falls_back_to_all(self):
        response = self.client.get(self.url + "?plant=banana")
        self.assertEqual(len(response.context["cards"]), Milestone.objects.count())

    def test_filter_with_no_milestones_shows_empty_message(self):
        Milestone.objects.filter(plant_type="herbs").delete()
        response = self.client.get(self.url + "?plant=herbs")
        self.assertContains(response, "No milestones for this plant yet")

    def test_percent_is_zero_with_no_milestones_at_all(self):
        Milestone.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.context["progress_percent"], 0)


class ClaimTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.url = reverse("achievements:claim_badge", args=["first-sprout"])

    def messages(self, response):
        return [str(message) for message in get_messages(response.wsgi_request)]

    def test_claim_works_once_progress_is_enough(self):
        record_progress(self.user, "plants_added")
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("achievements:show_achievements"))
        self.assertTrue(ClaimedBadge.objects.filter(user=self.user, milestone__slug="first-sprout").exists())
        self.assertIn("Badge claimed", self.messages(response)[0])

    def test_claim_is_refused_without_progress(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertEqual(ClaimedBadge.objects.count(), 0)

    def test_claiming_twice_keeps_one_row(self):
        record_progress(self.user, "plants_added")
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(ClaimedBadge.objects.count(), 1)

    def test_visitor_cannot_claim(self):
        response = self.client.post(self.url)
        self.assertEqual(ClaimedBadge.objects.count(), 0)
        self.assertIn("Log in first", self.messages(response)[0])

    def test_unknown_milestone_is_404(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:claim_badge", args=["nope"]))
        self.assertEqual(response.status_code, 404)

    def test_claim_only_accepts_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class CheckInViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.url = reverse("achievements:check_in")

    def test_check_in_creates_one_row_and_a_streak(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(CheckIn.objects.count(), 1)
        self.assertEqual(current_streak(self.user), 1)

    def test_visitor_cannot_check_in(self):
        response = self.client.post(self.url)
        self.assertEqual(CheckIn.objects.count(), 0)
        self.assertIn("Log in first", [str(m) for m in get_messages(response.wsgi_request)][0])

    def test_str_methods(self):
        milestone = Milestone.objects.get(slug="first-sprout")
        claim = ClaimedBadge.objects.create(user=self.user, milestone=milestone)
        check = CheckIn.objects.create(user=self.user, date=timezone.localdate())
        record_progress(self.user, "answers_given")
        self.assertEqual(str(milestone), "First Sprout")
        self.assertIn("rina claimed", str(claim))
        self.assertIn("rina on", str(check))
        self.assertIn("answers_given = 1", str(self.user.metrics.first()))