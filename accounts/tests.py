from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile, ProfileImage

PASSWORD = "tomatoes-4-all"


class ProfileSignalTests(TestCase):
    def test_profile_is_created_for_every_new_user(self):
        user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_saving_a_user_again_does_not_make_a_second_profile(self):
        user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        user.first_name = "Ben"
        user.save()
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)


class RegisterTests(TestCase):
    def valid_data(self, **changes):
        data = {
            "username": "ben", "email": "ben@example.com",
            "password1": PASSWORD, "password2": PASSWORD, "agree_terms": "on",
        }
        data.update(changes)
        return data

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("profile:register"), self.valid_data())
        self.assertRedirects(response, reverse("profile:show_profile"))
        self.assertTrue(User.objects.filter(username="ben").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_needs_the_checkbox(self):
        data = self.valid_data()
        del data["agree_terms"]
        response = self.client.post(reverse("profile:register"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_register_refuses_mismatched_passwords(self):
        response = self.client.post(reverse("profile:register"), self.valid_data(password2="something-else-1"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_register_refuses_duplicate_email(self):
        User.objects.create_user("sam", "ben@example.com", PASSWORD)
        response = self.client.post(reverse("profile:register"), self.valid_data(email="BEN@example.com"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="ben").exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)

    def test_login_with_right_password(self):
        response = self.client.post(reverse("profile:login"), {"username": "ben", "password": PASSWORD})
        self.assertRedirects(response, reverse("profile:show_profile"))

    def test_login_with_wrong_password(self):
        response = self.client.post(reverse("profile:login"), {"username": "ben", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_clears_session_and_goes_to_login(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:logout"))
        self.assertRedirects(response, reverse("profile:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class ProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)

    def test_profile_needs_login(self):
        response = self.client.get(reverse("profile:show_profile"))
        self.assertRedirects(response, reverse("profile:login") + "?next=" + reverse("profile:show_profile"))

    def test_profile_page_shows_the_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile:show_profile"))
        self.assertContains(response, "@ben")

    def test_edit_profile_saves_changes(self):
        from plants.models import Plant

        plant = Plant.objects.create(name="Test Tomato", slug="test-tomato-save")
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:edit_profile"), {
            "bio": "Learning composting", "location": "South Jakarta",
            "favorite_plant": plant.pk, "growing_style": "Balcony garden",
            "profile_picture": "", "cover_image": "",
        })
        self.assertRedirects(response, reverse("profile:show_profile"))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.favorite_plant, plant)
        self.assertEqual(profile.growing_style, "Balcony garden")

    def test_edit_profile_refuses_http_image_links(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:edit_profile"), {"picture_url": "http://example.com/a.jpg"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Profile.objects.get(user=self.user).profile_picture, "")


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class ImageUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.client.force_login(self.user)

    def edit(self, **extra):
        data = {"bio": "", "location": "", "favorite_plant": "", "growing_style": ""}
        data.update(extra)
        return self.client.post(reverse("profile:edit_profile"), data)

    def upload(self, name="me.png", content=PNG):
        return SimpleUploadedFile(name, content, content_type="image/png")

    def test_upload_profile_picture(self):
        response = self.edit(picture_file=self.upload())
        self.assertRedirects(response, reverse("profile:show_profile"))
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.profile_picture.startswith(reverse("profile:picture", args=["ben"])))
        image_response = self.client.get(reverse("profile:picture", args=["ben"]))
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Content-Type"], "image/png")

    def test_upload_profile_banner(self):
        self.edit(banner_file=self.upload("banner.png"))
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.cover_image.startswith(reverse("profile:banner", args=["ben"])))
        self.assertTrue(ProfileImage.objects.filter(profile=profile, kind="banner").exists())

    def test_upload_must_be_a_real_image(self):
        response = self.edit(picture_file=self.upload("fake.png", b"this is not an image"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProfileImage.objects.exists())

    def test_pasted_link_replaces_an_upload(self):
        self.edit(picture_file=self.upload())
        self.edit(picture_url="https://images.pexels.com/photos/1/a.jpg")
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.profile_picture, "https://images.pexels.com/photos/1/a.jpg")
        self.assertFalse(ProfileImage.objects.exists())

    def test_saving_again_keeps_the_upload(self):
        self.edit(picture_file=self.upload())
        self.edit(bio="Hello")
        self.assertTrue(ProfileImage.objects.filter(kind="avatar").exists())
        self.assertTrue(Profile.objects.get(user=self.user).profile_picture.startswith("/profile/ben/picture/"))

    def test_remove_picture(self):
        self.edit(picture_file=self.upload())
        self.edit(remove_picture="on")
        self.assertEqual(Profile.objects.get(user=self.user).profile_picture, "")
        self.assertFalse(ProfileImage.objects.exists())


class AvatarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ala", "ala@example.com", PASSWORD)

    def test_new_profile_gets_one_of_the_four_colors(self):
        self.assertIn(self.user.profile.avatar_color, ["green", "pink", "lilac", "yellow"])

    def test_color_never_changes_when_the_picture_is_added_and_removed(self):
        color = self.user.profile.avatar_color
        self.client.force_login(self.user)
        data = {"bio": "", "location": "", "favorite_plant": "", "growing_style": ""}
        self.client.post(reverse("profile:edit_profile"), {**data, "picture_url": "https://images.pexels.com/photos/1/a.jpg"})
        self.client.post(reverse("profile:edit_profile"), {**data, "remove_picture": "on"})
        self.assertEqual(Profile.objects.get(user=self.user).avatar_color, color)

    def test_initials(self):
        self.assertEqual(self.user.profile.initials, "A")
        self.user.first_name = "Ana Hill"
        self.user.save()
        self.assertEqual(Profile.objects.get(user=self.user).initials, "AH")


class AccountDeletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.client.force_login(self.user)

    def test_delete_page_needs_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile:delete_account"))
        self.assertRedirects(response, reverse("profile:login") + "?next=" + reverse("profile:delete_account"))

    def test_wrong_password_keeps_the_account(self):
        response = self.client.post(reverse("profile:delete_account"), {"password": "wrong-password", "confirm": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="ben").exists())

    def test_must_tick_the_box(self):
        response = self.client.post(reverse("profile:delete_account"), {"password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="ben").exists())

    def test_delete_removes_user_profile_and_logs_out(self):
        profile_id = self.user.profile.id
        response = self.client.post(reverse("profile:delete_account"), {"password": PASSWORD, "confirm": "on"})
        self.assertRedirects(response, reverse("profile:login"))
        self.assertFalse(User.objects.filter(username="ben").exists())
        self.assertFalse(Profile.objects.filter(id=profile_id).exists())
        self.assertNotIn("_auth_user_id", self.client.session)


class AvatarColorConsistencyTests(TestCase):
    def test_own_page_and_public_page_show_the_same_color(self):
        user = User.objects.create_user("ala", "ala@example.com", PASSWORD)
        viewer = User.objects.create_user("sam", "sam@example.com", PASSWORD)
        color_class = user.profile.avatar_bg_class
        self.client.force_login(user)
        own = self.client.get(reverse("profile:show_profile"))
        self.client.force_login(viewer)
        public = self.client.get(reverse("profile:show_user_profile", args=["ala"]))
        self.assertContains(own, color_class)
        self.assertContains(public, color_class)


class AvatarTagTests(TestCase):
    def render(self, template, **context):
        from django.template import Context, Template
        return Template("{% load accounts_tags %}" + template).render(Context(context))

    def test_avatar_tag_shows_initials_on_the_users_own_color(self):
        user = User.objects.create_user("ala", "ala@example.com", PASSWORD)
        html = self.render("{% avatar u %}", u=user)
        self.assertIn(user.profile.avatar_bg_class, html)
        self.assertIn(">A<", html)

    def test_avatar_tag_shows_the_picture_when_there_is_one(self):
        user = User.objects.create_user("ala", "ala@example.com", PASSWORD)
        Profile.objects.filter(user=user).update(profile_picture="https://images.pexels.com/photos/1/a.jpg")
        user = User.objects.get(pk=user.pk)
        html = self.render("{% avatar u %}", u=user)
        self.assertIn("https://images.pexels.com/photos/1/a.jpg", html)
        self.assertNotIn("AL", html)

    def test_filters_give_the_same_color_as_the_profile(self):
        user = User.objects.create_user("ala", "ala@example.com", PASSWORD)
        html = self.render("{{ u|avatar_bg_class }} {{ u|avatar_initials }}", u=user)
        self.assertEqual(html, f"{user.profile.avatar_bg_class} A")


class PublicProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        Profile.objects.filter(user=self.user).update(bio="Tomatoes only", location="South Jakarta")
        self.url = reverse("profile:show_user_profile", args=["ben"])

    def test_anyone_can_open_a_profile_without_logging_in(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "@ben")
        self.assertContains(response, "Tomatoes only")
        self.assertContains(response, "South Jakarta")

    def test_visitors_see_no_edit_button_and_no_email(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, reverse("profile:edit_profile"))
        self.assertNotContains(response, "ben@example.com")

    def test_another_logged_in_user_sees_no_edit_button(self):
        self.client.force_login(User.objects.create_user("sam", "sam@example.com", PASSWORD))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("profile:edit_profile"))

    def test_the_owner_sees_the_edit_button_on_their_own_public_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, reverse("profile:edit_profile"))

    def test_unknown_username_is_a_404(self):
        response = self.client.get(reverse("profile:show_user_profile", args=["nobody"]))
        self.assertEqual(response.status_code, 404)

    def test_my_profile_still_needs_a_login(self):
        response = self.client.get(reverse("profile:show_profile"))
        self.assertRedirects(response, reverse("profile:login") + "?next=" + reverse("profile:show_profile"))


class GardenSnapshotsTests(TestCase):
    def setUp(self):
        from garden.models import Post

        self.Post = Post
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.fan = User.objects.create_user("sam", "sam@example.com", PASSWORD)
        self.url = reverse("profile:show_user_profile", args=["ben"])

    def make_post(self, caption, **extra):
        return self.Post.objects.create(author=self.user, caption=caption, **extra)

    def test_profile_shows_only_the_four_newest_posts(self):
        for number in range(1, 7):
            self.make_post(f"Post number {number}.")
        response = self.client.get(self.url)
        for number in (3, 4, 5, 6):
            self.assertContains(response, f"Post number {number}.")
        for number in (1, 2):
            self.assertNotContains(response, f"Post number {number}.")

    def test_a_post_with_a_photo_link_shows_its_photo(self):
        self.make_post("First tomatoes", image_url="https://images.pexels.com/photos/1/a.jpg")
        response = self.client.get(self.url)
        self.assertContains(response, "https://images.pexels.com/photos/1/a.jpg")

    def test_other_peoples_posts_are_not_shown(self):
        self.Post.objects.create(author=self.fan, caption="Sam's basil")
        self.assertNotContains(self.client.get(self.url), "basil")

    def test_stats_count_posts_and_appreciations(self):
        from accounts.views import get_profile_stats

        first = self.make_post("One")
        second = self.make_post("Two")
        first.likes.add(self.fan)
        second.likes.add(self.fan, self.user)
        stats = {label: value for value, label in get_profile_stats(self.user)}
        self.assertEqual(stats["Garden posts"], "2")
        self.assertEqual(stats["Appreciations"], "3")

    def test_empty_profile_shows_the_empty_message(self):
        self.assertContains(self.client.get(self.url), "No garden posts yet")


class RecentBadgesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.other = User.objects.create_user("sam", "sam@example.com", PASSWORD)
        self.url = reverse("profile:show_user_profile", args=["ben"])

    def make_milestone(self, number, tone="bg-brand-soft"):
        from achievements.models import Milestone

        return Milestone.objects.create(
            slug=f"badge-{number}", title=f"Badge {number}", description="Test badge", metric="plants_added",
            target=1, icon="img/icons/ach-sprout-lg.svg", tone=tone,
        )

    def claim(self, milestone, user=None):
        from achievements.models import ClaimedBadge

        return ClaimedBadge.objects.create(user=user or self.user, milestone=milestone)

    def test_no_badges_shows_the_empty_message(self):
        self.assertContains(self.client.get(self.url), "No badges yet")

    def test_a_claimed_badge_shows_on_the_profile_with_its_color(self):
        self.claim(self.make_milestone(1, tone="bg-pink"))
        response = self.client.get(self.url)
        self.assertContains(response, "Badge 1")
        self.assertContains(response, "bg-pink")
        self.assertNotContains(response, "No badges yet")

    def test_only_the_three_newest_claims_are_shown(self):
        for number in range(1, 5):
            self.claim(self.make_milestone(number))
        response = self.client.get(self.url)
        for number in (2, 3, 4):
            self.assertContains(response, f"Badge {number}")
        self.assertNotContains(response, "Badge 1")

    def test_other_peoples_badges_are_not_shown(self):
        self.claim(self.make_milestone(1), user=self.other)
        self.assertNotContains(self.client.get(self.url), "Badge 1")

    def test_a_finished_but_unclaimed_badge_is_not_shown(self):
        self.make_milestone(1)
        self.assertNotContains(self.client.get(self.url), "Badge 1")

    def test_the_achievements_stat_counts_claimed_badges(self):
        from accounts.views import get_profile_stats

        self.claim(self.make_milestone(1))
        self.claim(self.make_milestone(2))
        stats = {label: value for value, label in get_profile_stats(self.user)}
        self.assertEqual(stats["Achievements"], "2")

    def test_view_all_is_only_for_the_owner(self):
        link = reverse("achievements:show_achievements")
        self.assertNotContains(self.client.get(self.url), f'href="{link}" class="text-[11px]')
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), f'href="{link}" class="text-[11px]')


class FavoritePlantTests(TestCase):
    def setUp(self):
        from plants.models import Plant

        self.plant = Plant.objects.create(name="Test Tomato", slug="test-tomato")
        self.user = User.objects.create_user("ben", "ben@example.com", PASSWORD)
        self.client.force_login(self.user)

    def edit(self, **extra):
        data = {"display_name": "", "bio": "", "location": "", "favorite_plant": "", "growing_style": ""}
        data.update(extra)
        return self.client.post(reverse("profile:edit_profile"), data)

    def test_pick_a_favorite_plant_from_the_list(self):
        self.edit(favorite_plant=self.plant.pk)
        self.assertEqual(Profile.objects.get(user=self.user).favorite_plant, self.plant)

    def test_the_edit_page_offers_the_plant_list_as_a_picker(self):
        response = self.client.get(reverse("profile:edit_profile"))
        self.assertContains(response, "data-plant-picker")
        self.assertContains(response, "Test Tomato")
        self.assertContains(response, "js/plant_picker.js")

    def test_the_favorite_plant_shows_on_the_profile_and_links_to_the_encyclopedia(self):
        self.edit(favorite_plant=self.plant.pk)
        response = self.client.get(reverse("profile:show_profile"))
        self.assertContains(response, "Test Tomato")
        self.assertContains(response, reverse("encyclopedia:detail", args=["test-tomato"]))

    def test_the_favorite_plant_can_be_cleared(self):
        self.edit(favorite_plant=self.plant.pk)
        self.edit(favorite_plant="")
        self.assertIsNone(Profile.objects.get(user=self.user).favorite_plant)

    def test_a_plant_that_does_not_exist_is_refused(self):
        response = self.edit(favorite_plant=999999)
        self.assertEqual(response.status_code, 200)
        self.assertIn("favorite_plant", response.context["form"].errors)
        self.assertIsNone(Profile.objects.get(user=self.user).favorite_plant)

    def test_deleting_the_plant_keeps_the_profile(self):
        self.edit(favorite_plant=self.plant.pk)
        self.plant.delete()
        profile = Profile.objects.get(user=self.user)
        self.assertIsNone(profile.favorite_plant)
