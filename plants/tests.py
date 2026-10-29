from django.test import TestCase

from plants import mapping
from plants.models import Plant


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