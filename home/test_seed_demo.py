from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from community.models import Question
from events.models import Event
from garden.models import Post


class SeedDemoTests(TestCase):
    def test_adds_demo_gardeners_once_and_removes_them(self):
        call_command("seed_demo", stdout=open("/dev/null", "w"))
        call_command("seed_demo", stdout=open("/dev/null", "w"))  # running twice adds nothing new
        self.assertEqual(User.objects.filter(username="rina.grows").count(), 1)
        self.assertEqual(Post.objects.count(), 6)
        self.assertEqual(Question.objects.count(), 3)
        self.assertEqual(Event.objects.count(), 2)
        self.assertFalse(User.objects.get(username="rina.grows").has_usable_password())
        call_command("seed_demo", "--remove", stdout=open("/dev/null", "w"))
        self.assertEqual(Post.objects.count(), 0)
        self.assertFalse(User.objects.filter(username="rina.grows").exists())
