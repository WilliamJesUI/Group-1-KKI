from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from achievements.forms import GoalForm, ProgressLogForm
from plants.models import Plant
from achievements.models import CheckIn, ClaimedBadge, Goal, Milestone, ProgressLog
from achievements.services import can_claim, check_in_today, current_streak, get_metric, record_progress


def make_plant(name="Cherry tomato", category="vegetables"):
    # The same fields the events tests use. The slug must be unique, so it comes from the name.
    return Plant.objects.get_or_create(name=name, defaults={"slug": slugify(name), "category": category})[0]


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


class GoalModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.goal = Goal.objects.create(user=self.user, title="Harvest 5 tomatoes", plant=make_plant(), target=5)

    def test_new_goal_has_no_progress(self):
        self.assertEqual((self.goal.done, self.goal.percent, self.goal.is_complete), (0, 0, False))

    def test_done_adds_up_all_logs(self):
        ProgressLog.objects.create(goal=self.goal, amount=2)
        ProgressLog.objects.create(goal=self.goal, amount=1)
        self.assertEqual(self.goal.done, 3)
        self.assertEqual(self.goal.percent, 60)
        self.assertFalse(self.goal.is_complete)

    def test_goal_is_complete_at_the_target_and_percent_is_capped(self):
        ProgressLog.objects.create(goal=self.goal, amount=5)
        ProgressLog.objects.create(goal=self.goal, amount=3)
        self.assertTrue(self.goal.is_complete)
        self.assertEqual(self.goal.percent, 100)

    def test_percent_rounds_down(self):
        ProgressLog.objects.create(goal=self.goal, amount=1)
        self.assertEqual(self.goal.percent, 20)
        other = Goal.objects.create(user=self.user, title="Water basil", plant=make_plant("Basil", "herbs"), target=3)
        ProgressLog.objects.create(goal=other, amount=2)
        self.assertEqual(other.percent, 66)

    def test_log_date_defaults_to_today(self):
        log = ProgressLog.objects.create(goal=self.goal)
        self.assertEqual((log.amount, log.date), (1, timezone.localdate()))

    def test_deleting_a_goal_deletes_its_logs(self):
        ProgressLog.objects.create(goal=self.goal, amount=2)
        self.goal.delete()
        self.assertEqual(ProgressLog.objects.count(), 0)

    def test_logs_are_listed_newest_date_first(self):
        old = ProgressLog.objects.create(goal=self.goal, date=timezone.localdate() - timedelta(days=3))
        new = ProgressLog.objects.create(goal=self.goal)
        self.assertEqual(list(self.goal.logs.all()), [new, old])

    def test_str_methods(self):
        log = ProgressLog.objects.create(goal=self.goal, amount=2)
        self.assertEqual(str(self.goal), "Harvest 5 tomatoes")
        self.assertIn("Harvest 5 tomatoes: +2 on", str(log))


class GoalFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.plant = make_plant()
        self.data = {"title": "Harvest 5 tomatoes", "plant": self.plant.pk, "target": 5}
        # For Goal.objects.create(): it needs the Plant itself, the form data above only has its id
        self.goal_fields = {"title": "Harvest 5 tomatoes", "plant": self.plant, "target": 5}

    def test_valid_goal_form(self):
        self.assertTrue(GoalForm(self.data).is_valid())

    def test_plant_must_come_from_the_list(self):
        form = GoalForm({**self.data, "plant": 99999})
        self.assertFalse(form.is_valid())
        self.assertIn("plant", form.errors)

    def test_plant_field_uses_the_plant_picker(self):
        html = str(GoalForm()["plant"])
        self.assertIn("data-plant-picker", html)
        self.assertIn("Choose a plant...", html)

    def test_edit_form_starts_with_the_goals_plant(self):
        goal = Goal.objects.create(user=self.user, **self.goal_fields)
        html = str(GoalForm(instance=goal)["plant"])
        self.assertRegex(html, f'<option value="{self.plant.id}"[^>]* selected')

    def test_empty_form_asks_for_the_required_fields(self):
        errors = GoalForm({}).errors
        self.assertEqual(errors["title"], ["Please give your goal a name."])
        self.assertEqual(errors["plant"], ["Please choose a plant."])
        self.assertEqual(errors["target"], ["Please say how many times."])

    def test_target_must_be_at_least_one(self):
        self.assertFalse(GoalForm({**self.data, "target": 0}).is_valid())

    def test_finish_by_cannot_be_in_the_past(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.assertIn("finish_by", GoalForm({**self.data, "finish_by": yesterday}).errors)
        self.assertTrue(GoalForm({**self.data, "finish_by": timezone.localdate()}).is_valid())

    def test_an_old_finish_date_is_fine_when_it_did_not_change(self):
        goal = Goal.objects.create(user=self.user, finish_by=timezone.localdate() - timedelta(days=5), **self.goal_fields)
        data = {**self.data, "title": "New name", "finish_by": goal.finish_by}
        self.assertTrue(GoalForm(data, instance=goal).is_valid())

    def test_target_cannot_drop_below_what_is_logged(self):
        goal = Goal.objects.create(user=self.user, **self.goal_fields)
        ProgressLog.objects.create(goal=goal, amount=3)
        form = GoalForm({**self.data, "target": 2}, instance=goal)
        self.assertFalse(form.is_valid())
        self.assertIn("already logged 3", form.errors["target"][0])

    def test_log_form_rejects_a_future_date(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.assertIn("date", ProgressLogForm({"amount": 1, "date": tomorrow}).errors)
        self.assertTrue(ProgressLogForm({"amount": 1, "date": timezone.localdate()}).is_valid())

    def test_log_form_needs_an_amount_and_a_date(self):
        errors = ProgressLogForm({}).errors
        self.assertEqual(errors["amount"], ["Please say how many."])
        self.assertEqual(errors["date"], ["Please pick a date."])


class GoalViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rina", password="pw")
        self.other = User.objects.create_user("sari", password="pw")
        self.plant = make_plant()
        self.data = {"title": "Harvest 5 tomatoes", "plant": self.plant.pk, "target": 5}
        # For Goal.objects.create(): it needs the Plant itself, the form data above only has its id
        self.goal_fields = {"title": "Harvest 5 tomatoes", "plant": self.plant, "target": 5}
        self.goal = Goal.objects.create(user=self.user, **self.goal_fields)
        self.page = reverse("achievements:show_achievements")

    def json_messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_create_makes_a_goal_for_the_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:create_goal"), {**self.data, "title": "Water basil"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Goal.objects.filter(user=self.user, title="Water basil").exists())
        self.assertIn("Goal started", self.json_messages(response)[0])
        self.assertIn("Log progress on it whenever you can.", self.json_messages(response)[0])

    def test_create_with_errors_returns_them_as_json(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:create_goal"), {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json()["errors"])

    def test_visitor_cannot_create(self):
        response = self.client.post(reverse("achievements:create_goal"), self.data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Goal.objects.count(), 1)

    def test_owner_can_edit(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:edit_goal", args=[self.goal.id]), {**self.data, "target": 8})
        self.assertEqual(response.status_code, 200)
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.target, 8)

    def test_edit_with_errors_returns_them(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:edit_goal", args=[self.goal.id]), {**self.data, "plant": ""})
        self.assertEqual(response.status_code, 400)

    def test_someone_else_cannot_edit_log_or_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("achievements:edit_goal", args=[self.goal.id]), self.data).status_code, 403)
        self.assertEqual(self.client.post(reverse("achievements:log_progress", args=[self.goal.id]), {"amount": 1, "date": timezone.localdate()}).status_code, 403)
        self.assertEqual(self.client.post(reverse("achievements:delete_goal", args=[self.goal.id])).status_code, 403)
        self.assertTrue(Goal.objects.filter(pk=self.goal.pk).exists())

    def test_visitor_cannot_edit_log_or_delete(self):
        self.assertEqual(self.client.post(reverse("achievements:edit_goal", args=[self.goal.id]), self.data).status_code, 403)
        self.assertEqual(self.client.post(reverse("achievements:log_progress", args=[self.goal.id]), {"amount": 1}).status_code, 403)
        self.assertEqual(self.client.post(reverse("achievements:delete_goal", args=[self.goal.id])).status_code, 403)

    def test_unknown_goal_is_404(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("achievements:edit_goal", args=[9999]), self.data).status_code, 404)

    def test_log_progress_returns_the_new_numbers(self):
        self.client.force_login(self.user)
        url = reverse("achievements:log_progress", args=[self.goal.id])
        response = self.client.post(url, {"amount": 3, "date": timezone.localdate(), "note": "Picked 3"})
        data = response.json()
        self.assertEqual((data["done"], data["percent"], data["is_complete"]), (3, 60, False))
        self.assertEqual(data["title"], "Progress saved")
        self.assertEqual(data["message"], "3 of 5 done. Keep going!")
        self.assertEqual(self.goal.logs.get().note, "Picked 3")

    def test_logging_the_last_amount_completes_the_goal(self):
        self.client.force_login(self.user)
        url = reverse("achievements:log_progress", args=[self.goal.id])
        data = self.client.post(url, {"amount": 5, "date": timezone.localdate()}).json()
        self.assertTrue(data["is_complete"])
        self.assertEqual(data["title"], "Goal complete")
        self.assertEqual(data["message"], "5 of 5 done. You did it!")

    def test_cannot_log_on_a_complete_goal(self):
        ProgressLog.objects.create(goal=self.goal, amount=5)
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:log_progress", args=[self.goal.id]), {"amount": 1, "date": timezone.localdate()})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.goal.logs.count(), 1)

    def test_log_with_errors_returns_them(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:log_progress", args=[self.goal.id]), {"amount": 0})
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())

    def test_owner_can_delete_and_the_logs_go_too(self):
        ProgressLog.objects.create(goal=self.goal, amount=2)
        self.client.force_login(self.user)
        response = self.client.post(reverse("achievements:delete_goal", args=[self.goal.id]))
        self.assertRedirects(response, self.page)
        self.assertEqual((Goal.objects.count(), ProgressLog.objects.count()), (0, 0))
        self.assertIn("Goal deleted", self.json_messages(response)[0])

    def test_delete_only_accepts_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("achievements:delete_goal", args=[self.goal.id])).status_code, 405)

    def test_page_lists_only_my_goals_with_their_progress(self):
        Goal.objects.create(user=self.other, title="Sari's secret goal", plant=make_plant("Mint", "herbs"), target=2)
        ProgressLog.objects.create(goal=self.goal, amount=3)
        self.client.force_login(self.user)
        response = self.client.get(self.page)
        self.assertContains(response, "Harvest 5 tomatoes")
        self.assertNotContains(response, "Sari&#x27;s secret goal")
        self.assertEqual(response.context["goals"][0].done, 3)

    def test_page_has_the_plant_picker(self):
        response = self.client.get(self.page)
        self.assertContains(response, "js/plant_picker.js")
        self.assertContains(response, "data-plant-picker")
        self.assertContains(response, f'<option value="{self.plant.id}"')

    def test_page_asks_visitors_to_log_in(self):
        response = self.client.get(self.page)
        self.assertContains(response, "Log in to start a goal")
        self.assertNotContains(response, "data-goal-new")