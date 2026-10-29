from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.urls import reverse

from community.models import Answer, Question
from events.models import Event
from plants.models import Plant
from .models import PlantCollection, SavedPlant
from .views import PLANT_TIPS, _require_authenticated, care_guide_for


class EncyclopediaTestData(TestCase):
    """Shared fixtures for the Encyclopedia view and collection tests."""

    def setUp(self):
        # The plants migration already loads the real plant list, so clear it
        # so these tests only see their own test plants (and slugs don't clash)
        Plant.objects.all().delete()
        self.user = User.objects.create_user(
            username="gardener",
            password="test-password-123",
        )
        self.other_user = User.objects.create_user(
            username="other-gardener",
            password="test-password-123",
        )
        self.basil = Plant.objects.create(
            name="Sweet Basil",
            slug="sweet-basil",
            scientific_name="Ocimum basilicum",
            family="Lamiaceae",
            category=Plant.Category.HERBS,
            difficulty=Plant.Difficulty.EASY,
            sunlight=Plant.Sunlight.FULL_SUN,
            watering=Plant.Watering.FREQUENT,
            watering_every="2-3 days",
            cycle=Plant.Cycle.ANNUAL,
            care_estimated=True,
            info_source="Trefle",
        )
        self.tomato = Plant.objects.create(
            name="Cherry Tomato",
            slug="cherry-tomato",
            scientific_name="Solanum lycopersicum",
            family="Solanaceae",
            category=Plant.Category.VEGETABLES,
            difficulty=Plant.Difficulty.MEDIUM,
            sunlight=Plant.Sunlight.PART_SHADE,
            watering=Plant.Watering.AVERAGE,
        )
        self.flower = Plant.objects.create(
            name="Marigold",
            slug="marigold",
            category=Plant.Category.FLOWERS,
            difficulty=Plant.Difficulty.HARD,
            sunlight=Plant.Sunlight.SHADE,
            watering=Plant.Watering.MINIMUM,
        )
        self.collection = PlantCollection.objects.create(
            user=self.user,
            name="Balcony Herbs",
        )
        self.collection_url = reverse("encyclopedia:collection")
        self.index_url = reverse("encyclopedia:index")


class EncyclopediaModelTests(EncyclopediaTestData):
    def test_saved_plant_string_representation(self):
        saved = SavedPlant.objects.create(user=self.user, plant=self.basil)
        self.assertEqual(str(saved), "gardener saved Sweet Basil")

    def test_collection_string_representation(self):
        self.assertEqual(str(self.collection), "Balcony Herbs")

    def test_saved_plant_is_unique_per_user_and_plant(self):
        SavedPlant.objects.create(user=self.user, plant=self.basil)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedPlant.objects.create(user=self.user, plant=self.basil)

    def test_collections_are_ordered_by_name(self):
        PlantCollection.objects.create(user=self.user, name="Window Box")
        self.assertEqual(
            list(PlantCollection.objects.filter(user=self.user).values_list("name", flat=True)),
            ["Balcony Herbs", "Window Box"],
        )


class CareGuideTests(EncyclopediaTestData):
    def test_known_plant_uses_species_specific_tips(self):
        guide = care_guide_for(self.basil)
        self.assertEqual(guide["specific_tips"], PLANT_TIPS["sweet-basil"])
        self.assertIn("herbs directory", guide["overview"])
        self.assertEqual(guide["source_label"], "Trefle")
        self.assertTrue(guide["care_is_estimated"])

    def test_unknown_plant_uses_fallback_tips(self):
        self.tomato.slug = "unlisted-plant"
        guide = care_guide_for(self.tomato)
        self.assertIn("Start Cherry Tomato", guide["specific_tips"][0])
        self.assertIn("Check cherry tomato weekly", guide["specific_tips"][1])
        self.assertEqual(guide["source_label"], "Grow Your Garden care notes")

    def test_sunlight_guidance_for_each_value(self):
        expected_phrases = {
            "full_sun": "direct sun",
            "full_sun_part_shade": "bright position",
            "part_shade": "filtered light",
            "shade": "shaded position",
            "": "Start in bright light",
        }
        for sunlight, phrase in expected_phrases.items():
            with self.subTest(sunlight=sunlight):
                self.basil.sunlight = sunlight
                self.assertIn(phrase, care_guide_for(self.basil)["light_note"])

    def test_watering_guidance_for_each_branch(self):
        self.basil.watering_every = "weekly"
        self.assertIn("every weekly", care_guide_for(self.basil)["water_note"])

        self.basil.watering_every = ""
        self.basil.watering = Plant.Watering.MINIMUM
        self.assertIn("dry substantially", care_guide_for(self.basil)["water_note"])

        self.basil.watering = Plant.Watering.FREQUENT
        self.assertIn("Check the soil often", care_guide_for(self.basil)["water_note"])

        self.basil.watering = Plant.Watering.AVERAGE
        self.assertIn("top layer begins to dry", care_guide_for(self.basil)["water_note"])

    def test_empty_category_uses_garden_label(self):
        self.basil.category = ""
        guide = care_guide_for(self.basil)
        self.assertIn("garden directory", guide["overview"])


class EncyclopediaDirectoryTests(EncyclopediaTestData):
    def test_directory_renders_for_anonymous_user(self):
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "encyclopedia.html")
        self.assertContains(response, "Sweet Basil")
        self.assertContains(response, "Log in")
        self.assertEqual(response.context["result_count"], 3)
        self.assertEqual(response.context["saved_ids"], set())

    def test_search_matches_name_scientific_name_and_family(self):
        for query, expected in (
            ("cherry", self.tomato),
            ("lycopersicum", self.tomato),
            ("Lamiaceae", self.basil),
        ):
            with self.subTest(query=query):
                response = self.client.get(self.index_url, {"q": query})
                self.assertEqual(list(response.context["plants"]), [expected])

    def test_category_and_difficulty_filters_can_be_combined(self):
        response = self.client.get(
            self.index_url,
            {"category": "vegetables", "difficulty": "medium"},
        )
        self.assertEqual(list(response.context["plants"]), [self.tomato])

    def test_unknown_filters_do_not_filter_the_directory(self):
        response = self.client.get(
            self.index_url,
            {"category": "unknown", "difficulty": "unknown"},
        )
        self.assertEqual(response.context["result_count"], 3)


    def test_level_pills_keep_the_other_filters(self):
        response = self.client.get(self.index_url, {"q": "a", "category": "herbs"})
        pills = {pill["label"]: pill for pill in response.context["difficulty_pills"]}
        # Only basil is a herb with "a" in it, so only "Easy" gets a pill
        self.assertEqual(list(pills), ["Easy"])
        self.assertFalse(pills["Easy"]["active"])
        self.assertEqual(pills["Easy"]["url"], "?q=a&category=herbs&difficulty=easy")

    def test_clicking_the_active_level_again_turns_it_off(self):
        response = self.client.get(self.index_url, {"category": "herbs", "difficulty": "easy"})
        pills = {pill["label"]: pill for pill in response.context["difficulty_pills"]}
        self.assertTrue(pills["Easy"]["active"])
        self.assertEqual(pills["Easy"]["url"], "?category=herbs")

    def test_category_pills_keep_the_level_and_search(self):
        response = self.client.get(self.index_url, {"q": "to", "difficulty": "medium"})
        pills = {pill["label"]: pill for pill in response.context["category_pills"]}
        self.assertEqual(pills["All"]["url"], "?q=to&difficulty=medium")
        self.assertEqual(pills["Vegetable"]["url"], "?q=to&category=vegetables&difficulty=medium")
        self.assertTrue(pills["All"]["active"])

    def test_other_level_pills_stay_when_one_is_picked(self):
        # Picking "Hard" must not hide the Easy and Medium pills
        response = self.client.get(self.index_url, {"difficulty": "hard"})
        labels = [pill["label"] for pill in response.context["difficulty_pills"]]
        self.assertEqual(labels, ["Easy", "Medium", "Hard"])
        self.assertEqual(list(response.context["plants"]), [self.flower])

    def test_search_form_keeps_category_and_level(self):
        response = self.client.get(self.index_url, {"category": "flowers", "difficulty": "hard"})
        self.assertContains(response, '<input type="hidden" name="category" value="flowers">', html=True)
        self.assertContains(response, '<input type="hidden" name="difficulty" value="hard">', html=True)
    
    def test_partial_sends_only_the_results(self):
        response = self.client.get(self.index_url, {"q": "basil", "partial": "1"})
        self.assertTemplateUsed(response, "plant_results.html")
        self.assertTemplateNotUsed(response, "encyclopedia.html")
        self.assertContains(response, "Sweet Basil")
        self.assertNotContains(response, "What should you grow next?")

    def test_full_page_loads_the_live_search_script(self):
        response = self.client.get(self.index_url)
        self.assertTemplateUsed(response, "plant_results.html")
        self.assertContains(response, "js/encyclopedia_search.js")

    def test_page_url_leaves_out_partial(self):
        # "Save to collection" sends you back here, so it must be the full page, not just the results
        response = self.client.get(self.index_url, {"q": "basil", "category": "herbs", "partial": "1"})
        self.assertEqual(response.context["page_url"], "/encyclopedia/?q=basil&category=herbs")

    def test_empty_category_lights_up_all(self):
        # The search form always sends category=, which means every category
        response = self.client.get(self.index_url, {"q": "", "category": "", "difficulty": ""})
        pills = {pill["label"]: pill for pill in response.context["category_pills"]}
        self.assertTrue(pills["All"]["active"])
        self.assertEqual(response.context["result_count"], 3)

    def test_difficulty_badge_color_matches_level(self):
        self.assertEqual(self.basil.difficulty_badge_class, "bg-brand-soft")
        self.assertEqual(self.tomato.difficulty_badge_class, "bg-butter")
        self.assertEqual(self.flower.difficulty_badge_class, "bg-pink")
        self.assertEqual(Plant(difficulty="").difficulty_badge_class, "bg-brand-soft")


    def test_authenticated_directory_shows_owned_collections_and_saved_ids(self):
        self.client.force_login(self.user)
        self.collection.plants.add(self.basil)
        response = self.client.get(self.index_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["collections"]), [self.collection])
        self.assertEqual(response.context["saved_ids"], {self.basil.pk})
        self.assertContains(response, "Manage collections")

    def test_detail_page_renders_guide_and_saved_state(self):
        self.client.force_login(self.user)
        self.collection.plants.add(self.basil)
        response = self.client.get(reverse("encyclopedia:detail", args=[self.basil.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "plant_detail.html")
        self.assertTrue(response.context["is_saved"])
        self.assertContains(response, "Sweet Basil")
        self.assertContains(response, "Pinch the growing tips")

    def test_detail_page_for_anonymous_user_has_no_collections(self):
        response = self.client.get(reverse("encyclopedia:detail", args=[self.basil.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_saved"])
        self.assertFalse(response.context["collections"].exists())

    def test_unknown_plant_detail_returns_404(self):
        response = self.client.get(reverse("encyclopedia:detail", args=["not-a-plant"]))
        self.assertEqual(response.status_code, 404)


class CollectionAccessTests(EncyclopediaTestData):
    def test_anonymous_collection_page_redirects_to_directory(self):
        response = self.client.get(self.collection_url)
        self.assertRedirects(response, self.index_url)
        self.assertTrue(list(get_messages(response.wsgi_request)))

    def test_collection_page_shows_first_collection_by_default(self):
        self.client.force_login(self.user)
        response = self.client.get(self.collection_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "collection.html")
        self.assertEqual(response.context["collection"], self.collection)

    def test_collection_page_can_select_a_collection(self):
        second = PlantCollection.objects.create(user=self.user, name="Window Box")
        self.client.force_login(self.user)
        response = self.client.get(self.collection_url, {"collection": second.pk})
        self.assertEqual(response.context["collection"], second)

    def test_unknown_collection_selection_shows_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(self.collection_url, {"collection": 99999})
        self.assertIsNone(response.context["collection"])

    def test_other_users_collections_are_not_listed(self):
        PlantCollection.objects.create(user=self.other_user, name="Private list")
        self.client.force_login(self.user)
        response = self.client.get(self.collection_url)
        self.assertNotContains(response, "Private list")

    def test_helper_rejects_anonymous_request(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        request.session = {}
        request._messages = FallbackStorage(request)
        self.assertFalse(_require_authenticated(request))

    def test_helper_accepts_authenticated_request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        self.assertTrue(_require_authenticated(request))


class CollectionMutationTests(EncyclopediaTestData):
    def test_create_collection_requires_authentication(self):
        response = self.client.post(
            reverse("encyclopedia:create_collection"),
            {"name": "New list"},
        )
        self.assertRedirects(response, self.index_url)
        self.assertEqual(PlantCollection.objects.count(), 1)

    def test_create_collection_rejects_blank_name(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("encyclopedia:create_collection"), {"name": "   "})
        self.assertRedirects(response, self.collection_url)
        self.assertEqual(PlantCollection.objects.count(), 1)

    def test_create_collection_trims_and_limits_name(self):
        self.client.force_login(self.user)
        name = "  " + ("A" * 110) + "  "
        response = self.client.post(reverse("encyclopedia:create_collection"), {"name": name})
        created = PlantCollection.objects.get(user=self.user, name__startswith="A")
        self.assertEqual(len(created.name), 100)
        self.assertRedirects(
            response,
            f"/encyclopedia/collection/?collection={created.pk}",
            fetch_redirect_response=False,
        )

    def test_create_collection_requires_post(self):
        response = self.client.get(reverse("encyclopedia:create_collection"))
        self.assertEqual(response.status_code, 405)

    def test_delete_collection_requires_authentication(self):
        response = self.client.post(
            reverse("encyclopedia:delete_collection", args=[self.collection.pk])
        )
        self.assertRedirects(response, self.index_url)
        self.assertTrue(PlantCollection.objects.filter(pk=self.collection.pk).exists())

    def test_delete_collection_removes_owned_collection(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("encyclopedia:delete_collection", args=[self.collection.pk])
        )
        self.assertRedirects(response, self.collection_url)
        self.assertFalse(PlantCollection.objects.filter(pk=self.collection.pk).exists())

    def test_user_cannot_delete_another_users_collection(self):
        self.client.force_login(self.user)
        other_collection = PlantCollection.objects.create(user=self.other_user, name="Private")
        response = self.client.post(
            reverse("encyclopedia:delete_collection", args=[other_collection.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_rename_collection(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.collection_url,
            {"collection_id": self.collection.pk, "name": "  Kitchen Herbs  "},
        )
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.name, "Kitchen Herbs")
        self.assertRedirects(
            response,
            f"/encyclopedia/collection/?collection={self.collection.pk}",
            fetch_redirect_response=False,
        )

    def test_blank_collection_rename_keeps_old_name(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.collection_url,
            {"collection_id": self.collection.pk, "name": "  "},
        )
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.name, "Balcony Herbs")
        self.assertEqual(response.status_code, 302)

    def test_user_cannot_rename_another_users_collection(self):
        self.client.force_login(self.user)
        other_collection = PlantCollection.objects.create(user=self.other_user, name="Private")
        response = self.client.post(
            self.collection_url,
            {"collection_id": other_collection.pk, "name": "Changed"},
        )
        self.assertEqual(response.status_code, 404)


class SaveAndRemovePlantTests(EncyclopediaTestData):
    def test_save_requires_post(self):
        response = self.client.get(reverse("encyclopedia:toggle_saved", args=[self.basil.slug]))
        self.assertEqual(response.status_code, 405)

    def test_anonymous_save_redirects_without_saving(self):
        response = self.client.post(
            reverse("encyclopedia:toggle_saved", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertRedirects(response, self.index_url)
        self.assertFalse(self.collection.plants.filter(pk=self.basil.pk).exists())

    def test_save_adds_plant_and_bookmark_record(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("encyclopedia:toggle_saved", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.collection.plants.filter(pk=self.basil.pk).exists())
        self.assertTrue(SavedPlant.objects.filter(user=self.user, plant=self.basil).exists())

    def test_toggle_removes_plant_and_bookmark_when_no_other_collection_has_it(self):
        self.client.force_login(self.user)
        self.collection.plants.add(self.basil)
        SavedPlant.objects.create(user=self.user, plant=self.basil)
        self.client.post(
            reverse("encyclopedia:toggle_saved", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertFalse(self.collection.plants.filter(pk=self.basil.pk).exists())
        self.assertFalse(SavedPlant.objects.filter(user=self.user, plant=self.basil).exists())

    def test_toggle_keeps_bookmark_while_plant_remains_in_another_collection(self):
        self.client.force_login(self.user)
        second = PlantCollection.objects.create(user=self.user, name="Other list")
        self.collection.plants.add(self.basil)
        second.plants.add(self.basil)
        SavedPlant.objects.create(user=self.user, plant=self.basil)
        self.client.post(
            reverse("encyclopedia:toggle_saved", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertTrue(second.plants.filter(pk=self.basil.pk).exists())
        self.assertTrue(SavedPlant.objects.filter(user=self.user, plant=self.basil).exists())

    def test_cannot_save_to_another_users_collection(self):
        self.client.force_login(self.user)
        other_collection = PlantCollection.objects.create(user=self.other_user, name="Private")
        response = self.client.post(
            reverse("encyclopedia:toggle_saved", args=[self.basil.slug]),
            {"collection_id": other_collection.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_remove_from_collection_requires_post(self):
        response = self.client.get(
            reverse("encyclopedia:remove_from_collection", args=[self.basil.slug])
        )
        self.assertEqual(response.status_code, 405)

    def test_remove_from_collection_cleans_up_bookmark(self):
        self.client.force_login(self.user)
        self.collection.plants.add(self.basil)
        SavedPlant.objects.create(user=self.user, plant=self.basil)
        response = self.client.post(
            reverse("encyclopedia:remove_from_collection", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedPlant.objects.filter(user=self.user, plant=self.basil).exists())

    def test_remove_from_collection_keeps_bookmark_if_saved_elsewhere(self):
        self.client.force_login(self.user)
        second = PlantCollection.objects.create(user=self.user, name="Other list")
        self.collection.plants.add(self.basil)
        second.plants.add(self.basil)
        SavedPlant.objects.create(user=self.user, plant=self.basil)
        self.client.post(
            reverse("encyclopedia:remove_from_collection", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertTrue(SavedPlant.objects.filter(user=self.user, plant=self.basil).exists())

    def test_cannot_remove_from_another_users_collection(self):
        self.client.force_login(self.user)
        other_collection = PlantCollection.objects.create(user=self.other_user, name="Private")
        response = self.client.post(
            reverse("encyclopedia:remove_from_collection", args=[self.basil.slug]),
            {"collection_id": other_collection.pk},
        )
        self.assertEqual(response.status_code, 404)


class AdditionalFailurePathTests(EncyclopediaTestData):
    def test_anonymous_remove_from_collection_redirects(self):
        response = self.client.post(
            reverse("encyclopedia:remove_from_collection", args=[self.basil.slug]),
            {"collection_id": self.collection.pk},
        )
        self.assertRedirects(response, self.index_url)
        self.assertFalse(self.collection.plants.filter(pk=self.basil.pk).exists())

    def test_missing_plant_save_returns_404_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("encyclopedia:toggle_saved", args=["missing-plant"]),
            {"collection_id": self.collection.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_collection_delete_returns_404(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("encyclopedia:delete_collection", args=[99999]),
        )
        self.assertEqual(response.status_code, 404)

    def test_saved_plant_model_orders_newest_first(self):
        first = SavedPlant.objects.create(user=self.user, plant=self.basil)
        second = SavedPlant.objects.create(user=self.other_user, plant=self.tomato)
        SavedPlant.objects.filter(pk=first.pk).update(
            saved_at=timezone.now() - timedelta(days=1)
        )
        saved_ids = list(SavedPlant.objects.values_list("pk", flat=True))
        self.assertEqual(saved_ids[0], second.pk)
        self.assertEqual(saved_ids[1], first.pk)

class PlantPageQuestionsAndEventsTests(EncyclopediaTestData):
    """The "Questions about ..." and "Events growing ..." sections on a plant page (Figma Plant Guide)."""

    def setUp(self):
        super().setUp()
        self.url = reverse("encyclopedia:detail", args=[self.basil.slug])

    def make_event(self, name, days, plant=None):
        start = timezone.now() + timedelta(days=days)
        return Event.objects.create(
            name=name, description="Bring gloves", location="Kemang", start_time=start,
            end_time=start + timedelta(hours=2), host=self.user, theme_plant=plant or self.basil,
        )

    def test_shows_newest_three_questions_with_answer_counts(self):
        for title in ["First", "Second", "Third", "Fourth"]:
            question = Question.objects.create(author=self.user, title=title, plant=self.basil)
        Answer.objects.create(question=question, author=self.other_user, body="Pinch it")
        Question.objects.create(author=self.user, title="About tomatoes", plant=self.tomato)
        response = self.client.get(self.url)
        questions = list(response.context["questions"])
        self.assertEqual([q.title for q in questions], ["Fourth", "Third", "Second"])
        self.assertEqual(questions[0].answer_count, 1)
        self.assertEqual(response.context["question_total"], 4)
        self.assertContains(response, "See all 4 questions")
        self.assertNotContains(response, "About tomatoes")

    def test_shows_only_upcoming_events_with_this_plant(self):
        soon = self.make_event("Basil swap", 3)
        later = self.make_event("Basil walk", 10)
        self.make_event("Old basil day", -5)
        self.make_event("Tomato day", 3, plant=self.tomato)
        response = self.client.get(self.url)
        self.assertEqual(response.context["plant_events"], [soon, later])
        self.assertEqual(response.context["event_total"], 2)
        self.assertContains(response, "Basil swap")
        self.assertNotContains(response, "Old basil day")

    def test_event_cards_know_if_the_user_is_going(self):
        event = self.make_event("Basil swap", 3)
        event.attendees.add(self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTrue(response.context["plant_events"][0].is_going)
        self.assertIn("csrftoken", response.cookies)

    def test_empty_sections_show_a_message(self):
        response = self.client.get(self.url)
        self.assertContains(response, "No questions about sweet basil yet.")
        self.assertContains(response, "No upcoming events with sweet basil yet.")
        self.assertContains(response, f'?plant={self.basil.slug}')
