import json
import tempfile
from importlib import import_module
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.apps import apps as django_apps
from django.core.management import call_command
from django.test import TestCase

from plants import mapping
from plants.management.commands import add_wikipedia_text
from plants.models import Plant
from plants.services import wikipedia
from plants.services.http import ApiError


class StarterPlantsTests(TestCase):
    def test_migration_loads_at_least_50_plants(self):
        self.assertGreaterEqual(Plant.objects.count(), 50)

    def test_every_plant_has_a_valid_category(self):
        valid = {"vegetables", "herbs", "flowers"}
        for plant in Plant.objects.all():
            self.assertIn(plant.category, valid, plant.name)

    def test_sweet_basil_matches_figma(self):
        basil = Plant.objects.get(slug="sweet-basil")
        self.assertEqual(basil.category, "herbs")
        self.assertEqual(basil.difficulty, "easy")
        self.assertEqual(basil.sunlight, "full_sun_part_shade")
        self.assertEqual(basil.watering, "frequent")
        self.assertEqual(basil.watering_every, "2-3 days")
        self.assertEqual(basil.cycle, "annual")

    def test_str_is_the_plant_name(self):
        self.assertEqual(str(Plant(name="Mint")), "Mint")


class MappingTests(TestCase):
    def test_basil_numbers_become_figma_words(self):
        species = {
            "id": 64847,
            "scientific_name": "Ocimum basilicum",
            "family": "Lamiaceae",
            "growth": {"light": 7, "soil_humidity": None},
            "duration": ["annual"],
            "specifications": {"growth_habit": "Forb/herb"},
        }
        fields = mapping.from_trefle(species, "herbs", "Sweet basil")
        self.assertEqual(fields["name"], "Sweet basil")
        self.assertEqual(fields["sunlight"], "full_sun_part_shade")
        self.assertEqual(fields["watering"], "frequent")
        self.assertEqual(fields["cycle"], "annual")
        self.assertEqual(fields["difficulty"], "easy")
        self.assertTrue(fields["care_estimated"])

    def test_empty_species_still_gives_safe_guesses(self):
        fields = mapping.from_trefle({}, "flowers", "Rose")
        self.assertEqual(fields["sunlight"], "full_sun")
        self.assertTrue(fields["care_estimated"])

class WikipediaTests(TestCase):
    """Fake Wikipedia answers, so the tests never need internet."""

    def fake_page(self, extract="Basil is a culinary herb of the mint family. It smells sweet and spicy. It is used in pesto.", kind="standard"):
        return {
            "type": kind,
            "extract": extract,
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Basil"}},
        }

    def test_summary_keeps_two_sentences_and_the_link(self):
        with patch("plants.services.wikipedia.get_json", return_value=self.fake_page()):
            found = wikipedia.summary("Ocimum basilicum")
        self.assertEqual(found["text"], "Basil is a culinary herb of the mint family. It smells sweet and spicy.")
        self.assertEqual(found["url"], "https://en.wikipedia.org/wiki/Basil")

    def test_summary_skips_list_pages(self):
        with patch("plants.services.wikipedia.get_json", return_value=self.fake_page(kind="disambiguation")):
            self.assertIsNone(wikipedia.summary("Mint"))

    def test_summary_gives_none_when_wikipedia_fails(self):
        with patch("plants.services.wikipedia.get_json", side_effect=ApiError("Timeout")):
            self.assertIsNone(wikipedia.summary("Ocimum basilicum"))

    def test_summary_without_a_title_asks_nothing(self):
        with patch("plants.services.wikipedia.get_json") as fake:
            self.assertIsNone(wikipedia.summary(""))
        fake.assert_not_called()

    def test_very_short_cut_keeps_the_full_text(self):
        text = "St. John's wort is a flowering plant used in teas."
        self.assertEqual(wikipedia.first_sentences(text, 1), text)

    def test_command_fills_descriptions_and_falls_back_to_the_english_name(self):
        plants = [
            {"name": "Sweet basil", "scientific_name": "Ocimum basilicum", "slug": "sweet-basil"},
            {"name": "Pandan", "scientific_name": "Pandanus amaryllifolius", "slug": "pandan"},
        ]
        answers = {
            "Ocimum basilicum": {"text": "Basil is a herb.", "url": "https://en.wikipedia.org/wiki/Basil"},
            "Pandan": {"text": "Pandan is a plant.", "url": "https://en.wikipedia.org/wiki/Pandan"},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plants.json"
            path.write_text(json.dumps(plants), encoding="utf-8")
            with patch.object(add_wikipedia_text, "DATA_DIR", Path(folder)), \
                    patch.object(add_wikipedia_text, "PAUSE_SECONDS", 0), \
                    patch("plants.services.wikipedia.summary", side_effect=answers.get):
                call_command("add_wikipedia_text", stdout=StringIO())
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["description"], "Basil is a herb.")
        self.assertEqual(saved[1]["description_url"], "https://en.wikipedia.org/wiki/Pandan")

    def test_command_lists_plants_it_could_not_find(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plants.json"
            path.write_text(json.dumps([{"name": "Mystery", "scientific_name": "", "slug": "mystery"}]))
            out = StringIO()
            with patch.object(add_wikipedia_text, "DATA_DIR", Path(folder)), \
                    patch.object(add_wikipedia_text, "PAUSE_SECONDS", 0), \
                    patch("plants.services.wikipedia.summary", return_value=None):
                call_command("add_wikipedia_text", stdout=out)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("missing 1: Mystery", out.getvalue())
        self.assertNotIn("description", saved[0])

    def test_command_skips_plants_that_already_have_a_description(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plants.json"
            path.write_text(json.dumps([{"name": "Tomato", "slug": "tomato", "description": "Done before."}]))
            with patch.object(add_wikipedia_text, "DATA_DIR", Path(folder)), \
                    patch("plants.services.wikipedia.summary") as fake:
                call_command("add_wikipedia_text", stdout=StringIO())
        fake.assert_not_called()

    def test_migration_copies_only_the_description(self):
        migration = import_module("plants.migrations.0004_load_wikipedia_text")
        plant = Plant.objects.get(slug="tomato")
        rows = [{"slug": "tomato", "name": "Changed", "description": "Tomato is a fruit.",
                 "description_url": "https://en.wikipedia.org/wiki/Tomato"}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plants.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            with patch.object(migration, "DATA_FILE", path):
                migration.load_descriptions(django_apps, None)
        plant.refresh_from_db()
        self.assertEqual(plant.description, "Tomato is a fruit.")
        self.assertEqual(plant.name, "Tomato")


class PlantPhotoTest(TestCase):
    """card_image_url / thumb_image_url use our saved copy in static/img/plants/ when there is one."""

    def setUp(self):
        from plants.models import Plant
        self.plant = Plant(name="Test basil", slug="test-basil", image_url="https://bs.plantnet.org/image/o/abc")

    def test_saved_copy_wins(self):
        with patch("plants.models.saved_plant_photos", return_value={"test-basil-m.jpg", "test-basil-s.jpg"}):
            self.assertEqual(self.plant.card_image_url, "/static/img/plants/test-basil-m.jpg")
            self.assertEqual(self.plant.thumb_image_url, "/static/img/plants/test-basil-s.jpg")

    def test_falls_back_to_plantnet(self):
        with patch("plants.models.saved_plant_photos", return_value=set()):
            self.assertEqual(self.plant.card_image_url, "https://bs.plantnet.org/image/o/abc".replace("/o/", "/m/"))
            self.assertEqual(self.plant.thumb_image_url, "https://bs.plantnet.org/image/s/abc")

    def test_no_photo(self):
        self.plant.image_url = ""
        self.assertEqual(self.plant.card_image_url, "")

    def test_credit_follows_the_photo(self):
        self.plant.image_credit, self.plant.image_credit_url = "Photo by PlantNet user", "https://plantnet.org"
        saved = {"test-basil": {"credit": "Photo by Ann, CC BY-SA 4.0 (Wikimedia Commons)", "url": "https://commons.wikimedia.org/x"}}
        with patch("plants.models.saved_photo_credits", return_value=saved):
            with patch("plants.models.saved_plant_photos", return_value={"test-basil-m.jpg"}):
                self.assertEqual(self.plant.photo_credit, "Photo by Ann, CC BY-SA 4.0 (Wikimedia Commons)")
                self.assertEqual(self.plant.photo_credit_url, "https://commons.wikimedia.org/x")
            # No saved photo, so the PlantNet photo shows with its own credit
            with patch("plants.models.saved_plant_photos", return_value=set()):
                self.assertEqual(self.plant.photo_credit, "Photo by PlantNet user")
                self.assertEqual(self.plant.photo_credit_url, "https://plantnet.org")

    def test_reads_the_folder(self):
        from plants.models import saved_photo_credits, saved_plant_photos
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "mint-s.jpg").write_bytes(b"x")
            Path(folder, "notes.txt").write_text("not a photo")
            saved_plant_photos.cache_clear()
            saved_photo_credits.cache_clear()
            with patch("plants.models.PLANT_PHOTO_DIR", Path(folder)):
                self.assertEqual(saved_plant_photos(), {"mint-s.jpg"})
                self.assertEqual(saved_photo_credits(), {})
                saved_photo_credits.cache_clear()
                Path(folder, "credits.json").write_text('{"mint": {"credit": "Photo by Ann", "url": ""}}')
                self.assertEqual(saved_photo_credits()["mint"]["credit"], "Photo by Ann")
            saved_plant_photos.cache_clear()
            saved_photo_credits.cache_clear()
