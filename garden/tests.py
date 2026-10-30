import importlib
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from garden.forms import MAX_PHOTO_SIZE, CommentForm, PostForm
from garden.models import Comment, PlantOfTheWeek, Post, short_age
from garden.views import get_plant_of_the_week
from growyourgarden.permissions import ajax_login_required, ajax_moderator_required, can_delete, is_moderator
from plants.models import Plant

# The first bytes of every PNG file, plus some filler
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100


def png_upload(name="basil.png", data=PNG_BYTES):
    return SimpleUploadedFile(name, data, content_type="image/png")


class GardenTestCase(TestCase):
    """Two members (siti and budi), one moderator (mod), two plants and one post by siti."""

    def setUp(self):
        self.siti = User.objects.create_user("siti", password="basil12345")
        self.budi = User.objects.create_user("budi", password="tomato12345")
        self.mod = User.objects.create_user("mod", password="admin12345", is_staff=True)
        self.basil = Plant.objects.create(name="Sweet basil", slug="test-basil", category="herbs", image_url="https://example.com/basil.jpg")
        self.tomato = Plant.objects.create(name="Tomato", slug="test-tomato", category="vegetables")
        self.post = Post.objects.create(author=self.siti, caption="My basil is huge", plant=self.basil)

    def login(self, user):
        self.client.force_login(user)


class PermissionsTest(TestCase):
    def setUp(self):
        self.member = User.objects.create_user("member")
        self.other = User.objects.create_user("other")
        self.staff = User.objects.create_user("staff", is_staff=True)
        self.factory = RequestFactory()

    def test_is_moderator(self):
        self.assertTrue(is_moderator(self.staff))
        self.assertFalse(is_moderator(self.member))
        self.assertFalse(is_moderator(AnonymousUser()))

    def test_can_delete(self):
        self.assertTrue(can_delete(self.member, self.member))
        self.assertTrue(can_delete(self.staff, self.member))
        self.assertFalse(can_delete(self.other, self.member))
        self.assertFalse(can_delete(AnonymousUser(), self.member))

    def run_view(self, decorator, user):
        view = decorator(lambda request: HttpResponse("ok"))
        request = self.factory.post("/")
        request.user = user
        return view(request)

    def test_ajax_login_required(self):
        response = self.run_view(ajax_login_required("Log in please."), AnonymousUser())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"message": "Log in please."})
        self.assertEqual(self.run_view(ajax_login_required(), self.member).content, b"ok")

    def test_ajax_moderator_required(self):
        response = self.run_view(ajax_moderator_required("Mods only."), self.member)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {"message": "Mods only."})
        self.assertEqual(self.run_view(ajax_moderator_required(), AnonymousUser()).status_code, 403)
        self.assertEqual(self.run_view(ajax_moderator_required(), self.staff).content, b"ok")


class ShortAgeTest(TestCase):
    def test_labels(self):
        now = timezone.now()
        self.assertEqual(short_age(now), "just now")
        self.assertEqual(short_age(now - timedelta(minutes=5)), "5 min")
        self.assertEqual(short_age(now - timedelta(hours=3)), "3 hr")
        self.assertEqual(short_age(now - timedelta(days=2)), "2 d")
        old = now - timedelta(days=30)
        local = timezone.localtime(old)
        self.assertEqual(short_age(old), f"{local.day} {local:%b}")


class ModelTest(GardenTestCase):
    def test_str_and_labels(self):
        self.assertIn("My basil", str(self.post))
        self.assertEqual(self.post.age_label, "just now")
        comment = Comment.objects.create(post=self.post, author=self.budi, text="Wow")
        self.assertEqual(str(comment), "Comment by budi")
        self.assertEqual(comment.age_label, "just now")
        pick = PlantOfTheWeek.objects.create(plant=self.basil)
        self.assertIn("Sweet basil", str(pick))

    def test_photo_src(self):
        self.assertEqual(self.post.photo_src, "")
        self.post.image_url = "https://example.com/old.jpg"
        self.assertEqual(self.post.photo_src, "https://example.com/old.jpg")
        self.post.photo = PNG_BYTES
        self.post.photo_type = "image/png"
        self.post.save()
        self.assertTrue(self.post.photo_src.startswith(reverse("garden:show_post_photo", args=[self.post.id]) + "?v="))


class PostFormTest(TestCase):
    def test_blank_caption(self):
        form = PostForm(data={"caption": "   "})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["caption"], ["Please write a caption."])

    def test_good_photo(self):
        form = PostForm(data={"caption": "Hi"}, files={"photo_upload": png_upload()})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["photo_upload"], {"data": PNG_BYTES, "type": "image/png"})

    def test_photo_too_big(self):
        big = png_upload(data=PNG_BYTES + b"0" * MAX_PHOTO_SIZE)
        form = PostForm(data={"caption": "Hi"}, files={"photo_upload": big})
        self.assertFalse(form.is_valid())
        self.assertIn("under 2 MB", form.errors["photo_upload"][0])

    def test_not_an_image(self):
        form = PostForm(data={"caption": "Hi"}, files={"photo_upload": png_upload("notes.png", b"just some text")})
        self.assertFalse(form.is_valid())
        self.assertIn("JPG, PNG or WebP", form.errors["photo_upload"][0])

    def test_blank_comment(self):
        form = CommentForm(data={"text": "  "})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["text"], ["Please write a comment first."])


class ShowGardenTest(GardenTestCase):
    def test_page_logged_out(self):
        response = self.client.get(reverse("garden:show_garden"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "garden/garden.html")
        self.assertContains(response, "My basil is huge")
        self.assertContains(response, "Log in to share")
        # "My posts" only makes sense when logged in
        self.assertNotContains(response, 'data-filter="mine"')
        self.assertNotContains(response, 'id="week-modal"')

    def test_author_links_to_profile(self):
        Comment.objects.create(post=self.post, author=self.budi, text="Wow")
        response = self.client.get(reverse("garden:show_garden"))
        self.assertContains(response, f'href="{reverse("profile:show_user_profile", args=["siti"])}"')
        # Comments are loaded on their own when the comment button is clicked
        response = self.client.get(reverse("garden:show_comments", args=[self.post.id]))
        self.assertContains(response, f'href="{reverse("profile:show_user_profile", args=["budi"])}"')

    def test_page_logged_in(self):
        self.login(self.budi)
        response = self.client.get(reverse("garden:show_garden"))
        self.assertContains(response, 'data-filter="mine"')
        self.assertContains(response, 'id="post-modal"')
        # budi didn't write the post, so no ••• menu on it
        self.assertFalse(response.context["posts"][0].can_edit)
        self.assertFalse(response.context["posts"][0].can_delete)

    def test_author_and_moderator_menu(self):
        self.login(self.siti)
        post = self.client.get(reverse("garden:show_garden")).context["posts"][0]
        self.assertTrue(post.can_edit and post.can_delete)
        self.login(self.mod)
        response = self.client.get(reverse("garden:show_garden"))
        post = response.context["posts"][0]
        self.assertFalse(post.can_edit)
        self.assertTrue(post.can_delete)
        self.assertContains(response, 'id="week-modal"')

    def test_filters(self):
        Post.objects.create(author=self.budi, caption="Tomatoes!", plant=self.tomato)
        Post.objects.create(author=self.budi, caption="No plant here")
        url = reverse("garden:show_garden")

        def captions(query):
            return [post.caption for post in self.client.get(url, query).context["posts"]]

        self.assertEqual(len(captions({"filter": "all"})), 3)
        self.assertEqual(captions({"filter": "herbs"}), ["My basil is huge"])
        self.assertEqual(captions({"filter": "vegetables"}), ["Tomatoes!"])
        self.assertEqual(captions({"filter": "flowers"}), [])
        self.assertEqual(len(captions({"filter": "nonsense"})), 3)
        self.assertEqual(captions({"filter": "mine"}), [])  # logged out
        self.assertEqual(captions({"plant": "test-tomato"}), ["Tomatoes!"])
        self.assertEqual(len(captions({"plant": "no-such-plant"})), 3)
        self.login(self.budi)
        self.assertEqual(sorted(captions({"filter": "mine"})), ["No plant here", "Tomatoes!"])

    def test_partial_feed(self):
        response = self.client.get(reverse("garden:show_garden"), {"filter": "flowers", "partial": "1"})
        self.assertTemplateUsed(response, "garden/post_feed.html")
        self.assertTemplateNotUsed(response, "garden/garden.html")
        self.assertContains(response, "No posts here yet")

    def test_empty_states(self):
        Post.objects.all().delete()
        url = reverse("garden:show_garden")
        self.assertContains(self.client.get(url), "No posts yet")
        self.assertContains(self.client.get(url, {"plant": "test-basil"}), "Nobody has posted about Sweet basil yet.")
        self.login(self.budi)
        self.assertContains(self.client.get(url, {"filter": "mine"}), "You haven't posted yet")

    def test_upcoming_events(self):
        start = timezone.now() + timedelta(days=2)
        Event.objects.create(host=self.budi, name="Seed swap", location="Depok", start_time=start, end_time=start + timedelta(hours=2))
        self.assertContains(self.client.get(reverse("garden:show_garden")), "Seed swap")

    def test_same_number_of_queries(self):
        # More posts must not mean more queries (no query per card)
        self.login(self.budi)
        url = reverse("garden:show_garden")
        self.client.get(url)
        with self.assertNumQueries(9):
            self.client.get(url)
        for number in range(5):
            Post.objects.create(author=self.siti, caption=f"post {number}", plant=self.tomato)
        with self.assertNumQueries(9):
            self.client.get(url)


class PlantOfTheWeekTest(GardenTestCase):
    def test_admin_pick_wins(self):
        PlantOfTheWeek.objects.create(plant=self.tomato, short_line="Juicy")
        self.assertEqual(get_plant_of_the_week(), (self.tomato, "Juicy"))

    def test_weekly_fallback_uses_plants_with_photos(self):
        # Only basil has a photo, so it's picked every week
        Plant.objects.exclude(pk=self.basil.pk).update(image_url="")
        self.assertEqual(get_plant_of_the_week(), (self.basil, ""))

    def test_no_plants(self):
        Plant.objects.update(image_url="")
        self.assertEqual(get_plant_of_the_week(), (None, ""))

    def test_set_by_moderator(self):
        self.login(self.mod)
        response = self.client.post(reverse("garden:set_plant_of_the_week"), {"plant": self.tomato.id, "short_line": "Easy to grow"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tomato", response.json()["html"])
        self.assertIn("Easy to grow", response.json()["html"])
        self.assertEqual(PlantOfTheWeek.objects.get().plant, self.tomato)

    def test_set_needs_a_plant(self):
        self.login(self.mod)
        response = self.client.post(reverse("garden:set_plant_of_the_week"), {"plant": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["plant"][0]["message"], "Please pick a plant.")

    def test_members_cannot_set(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:set_plant_of_the_week"), {"plant": self.tomato.id})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PlantOfTheWeek.objects.exists())


class CreateAndEditPostTest(GardenTestCase):
    def test_create(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:create_post"), {"caption": " Look! ", "plant": self.tomato.id, "photo_upload": png_upload()})
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(author=self.budi)
        self.assertEqual(post.caption, "Look!")
        self.assertEqual(post.plant, self.tomato)
        self.assertEqual(bytes(post.photo), PNG_BYTES)
        self.assertIn("Look!", response.json()["html"])

    def test_create_errors(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:create_post"), {"caption": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"]["caption"][0]["message"], "Please write a caption.")

    def test_create_logged_out(self):
        response = self.client.post(reverse("garden:create_post"), {"caption": "Hi"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "Please log in to share a post.")

    def test_edit(self):
        self.login(self.siti)
        response = self.client.post(reverse("garden:edit_post", args=[self.post.id]), {"caption": "Even bigger", "plant": ""})
        self.assertEqual(response.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.caption, "Even bigger")
        self.assertIsNone(self.post.plant)

    def test_edit_errors(self):
        self.login(self.siti)
        response = self.client.post(reverse("garden:edit_post", args=[self.post.id]), {"caption": ""})
        self.assertEqual(response.status_code, 400)

    def test_edit_remove_photo(self):
        self.post.photo = PNG_BYTES
        self.post.photo_type = "image/png"
        self.post.image_url = "https://example.com/old.jpg"
        self.post.save()
        self.login(self.siti)
        self.client.post(reverse("garden:edit_post", args=[self.post.id]), {"caption": "No photo", "remove_photo": "True"})
        self.post.refresh_from_db()
        self.assertIsNone(self.post.photo)
        self.assertEqual(self.post.photo_type, "")
        self.assertEqual(self.post.image_url, "")

    def test_only_author_edits(self):
        # Not even a moderator can change someone else's words
        for user in (self.budi, self.mod):
            self.login(user)
            response = self.client.post(reverse("garden:edit_post", args=[self.post.id]), {"caption": "Hacked"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["message"], "You can only edit your own posts.")
        self.post.refresh_from_db()
        self.assertEqual(self.post.caption, "My basil is huge")

    def test_get_not_allowed(self):
        self.login(self.siti)
        self.assertEqual(self.client.get(reverse("garden:create_post")).status_code, 405)


class PhotoTest(GardenTestCase):
    def test_photo(self):
        self.post.photo = PNG_BYTES
        self.post.photo_type = "image/png"
        self.post.save()
        response = self.client.get(reverse("garden:show_post_photo", args=[self.post.id]))
        self.assertEqual(response.content, PNG_BYTES)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "public, max-age=86400")

    def test_no_photo(self):
        self.assertEqual(self.client.get(reverse("garden:show_post_photo", args=[self.post.id])).status_code, 404)


class DeletePostTest(GardenTestCase):
    def test_author_deletes(self):
        self.login(self.siti)
        response = self.client.post(reverse("garden:delete_post", args=[self.post.id]))
        self.assertEqual(response.json(), {"deleted": True})
        self.assertFalse(Post.objects.exists())

    def test_moderator_deletes(self):
        self.login(self.mod)
        self.client.post(reverse("garden:delete_post", args=[self.post.id]))
        self.assertFalse(Post.objects.exists())

    def test_others_cannot_delete(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:delete_post", args=[self.post.id]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "You can only delete your own posts.")
        self.assertTrue(Post.objects.exists())


class LikeTest(GardenTestCase):
    def test_like_and_unlike(self):
        self.login(self.budi)
        url = reverse("garden:like_post", args=[self.post.id])
        self.assertEqual(self.client.post(url, {"liked": "true"}).json(), {"liked": True, "like_count": 1})
        # Liking twice (double click, two tabs) still counts once
        self.assertEqual(self.client.post(url, {"liked": "true"}).json(), {"liked": True, "like_count": 1})
        self.assertEqual(self.client.post(url, {"liked": "false"}).json(), {"liked": False, "like_count": 0})

    def test_feed_shows_my_like(self):
        self.post.likes.add(self.budi)
        self.login(self.budi)
        post = self.client.get(reverse("garden:show_garden")).context["posts"][0]
        self.assertTrue(post.is_liked)
        self.assertEqual(post.like_count, 1)

    def test_logged_out(self):
        response = self.client.post(reverse("garden:like_post", args=[self.post.id]), {"liked": "true"})
        self.assertEqual(response.status_code, 403)


class CommentTest(GardenTestCase):
    def add(self, author, text):
        return Comment.objects.create(post=self.post, author=author, text=text)

    def test_show_newest_three(self):
        for number in range(5):
            self.add(self.budi, f"comment {number}")
        response = self.client.get(reverse("garden:show_comments", args=[self.post.id]))
        self.assertEqual([c.text for c in response.context["comments"]], ["comment 2", "comment 3", "comment 4"])
        self.assertEqual(response.context["hidden_count"], 2)
        self.assertContains(response, "Show all 5 comments")
        response = self.client.get(reverse("garden:show_comments", args=[self.post.id]), {"all": "1"})
        self.assertEqual(len(response.context["comments"]), 5)
        self.assertEqual(response.context["hidden_count"], 0)

    def test_no_comments(self):
        response = self.client.get(reverse("garden:show_comments", args=[self.post.id]))
        self.assertContains(response, "data-no-comments")

    def test_add(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:add_comment", args=[self.post.id]), {"text": " So green "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["comment_count"], 1)
        self.assertIn("So green", response.json()["html"])
        self.assertEqual(Comment.objects.get().text, "So green")

    def test_add_errors(self):
        self.login(self.budi)
        response = self.client.post(reverse("garden:add_comment", args=[self.post.id]), {"text": ""})
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        response = self.client.post(reverse("garden:add_comment", args=[self.post.id]), {"text": "Hi"})
        self.assertEqual(response.status_code, 403)

    def test_delete_own_and_by_moderator(self):
        first = self.add(self.budi, "one")
        second = self.add(self.budi, "two")
        self.login(self.budi)
        response = self.client.post(reverse("garden:delete_comment", args=[first.id]))
        self.assertEqual(response.json(), {"comment_count": 1})
        self.login(self.mod)
        self.client.post(reverse("garden:delete_comment", args=[second.id]))
        self.assertFalse(Comment.objects.exists())

    def test_others_cannot_delete(self):
        comment = self.add(self.budi, "mine")
        # siti owns the post, but not the comment
        self.login(self.siti)
        response = self.client.post(reverse("garden:delete_comment", args=[comment.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.exists())


class LinkPlantTagsMigrationTest(TestCase):
    """The data step in migration 0015 that turns the old free-text plant tag into a real plant."""

    def test_links_by_name_or_slug(self):
        migration = importlib.import_module("garden.migrations.0015_link_posts_to_plants")
        basil = SimpleNamespace(name="Sweet basil", slug="sweet-basil")
        posts = [SimpleNamespace(plant_tag=tag, plant=None, save=mock.Mock()) for tag in ("sweet BASIL ", "Sweet-Basil", "Nonsense")]
        Plant = mock.Mock()
        Plant.objects.all.return_value = [basil]
        Post = mock.Mock()
        Post.objects.exclude.return_value = posts
        apps = mock.Mock()
        apps.get_model.side_effect = lambda app, name: {"Plant": Plant, "Post": Post}[name]

        migration.link_plant_tags(apps, None)

        self.assertEqual([post.plant for post in posts], [basil, basil, None])
        posts[0].save.assert_called_once_with(update_fields=["plant"])
        posts[2].save.assert_not_called()


class PlantPageSectionTest(GardenTestCase):
    """The "From the garden" section on each plant's Encyclopedia page."""

    def test_shows_newest_three_posts(self):
        for number in range(3):
            Post.objects.create(author=self.budi, caption=f"basil {number}", plant=self.basil)
        response = self.client.get(reverse("encyclopedia:detail", args=[self.basil.slug]))
        self.assertContains(response, "From the garden")
        self.assertEqual(len(response.context["garden_posts"]), 3)
        self.assertEqual(response.context["garden_post_total"], 4)
        self.assertContains(response, "See all 4 posts")
        self.assertContains(response, f"/garden/?plant={self.basil.slug}")

    def test_no_posts(self):
        response = self.client.get(reverse("encyclopedia:detail", args=[self.tomato.slug]))
        self.assertEqual(response.context["garden_post_total"], 0)
        self.assertNotContains(response, "See all")
