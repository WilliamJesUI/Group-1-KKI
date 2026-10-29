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
        self.client.force_login(self.user)
        response = self.client.post(reverse("profile:edit_profile"), {
            "bio": "Learning composting", "location": "South Jakarta",
            "favorite_plant": "Cherry Tomato", "growing_style": "Balcony garden",
            "profile_picture": "", "cover_image": "",
        })
        self.assertRedirects(response, reverse("profile:show_profile"))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.favorite_plant, "Cherry Tomato")
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
        self.assertEqual(self.user.profile.initials, "AL")
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
        self.assertIn("AL", html)

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
        self.assertEqual(html, f"{user.profile.avatar_bg_class} AL")
