import base64

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from accounts.models import Profile, ProfileImage
from plants.models import Plant

# A real 1x1 PNG, so detect_image_type() accepts it
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
GOOD_PASSWORD = "Sunflower-Garden-42"


def register_data(**overrides):
    data = {
        "username": "ben", "email": "ben@example.com",
        "password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD, "agree_terms": True,
    }
    data.update(overrides)
    return data


class RegisterAPITests(APITestCase):
    def test_register_creates_user_profile_and_logs_in(self):
        response = self.client.post(reverse("profile:api_register"), register_data(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "ben")
        self.assertEqual(response.data["email"], "ben@example.com")
        self.assertTrue(Profile.objects.filter(user__username="ben").exists())
        # logged in: the session works for the next request
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 200)

    def test_password_is_not_in_the_response(self):
        response = self.client.post(reverse("profile:api_register"), register_data(), format="json")
        self.assertNotIn("password1", response.data)
        self.assertNotIn("password", response.data)

    def test_needs_the_checkbox(self):
        response = self.client.post(reverse("profile:api_register"), register_data(agree_terms=False), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("agree_terms", response.data)

    def test_refuses_mismatched_passwords(self):
        response = self.client.post(reverse("profile:api_register"), register_data(password2="other"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password2", response.data)

    def test_refuses_weak_password_on_password1(self):
        response = self.client.post(
            reverse("profile:api_register"), register_data(password1="12345678", password2="12345678"), format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password1", response.data)
        self.assertEqual(User.objects.count(), 0)

    def test_refuses_duplicate_email_ignoring_case(self):
        User.objects.create_user("old", "BEN@example.com", GOOD_PASSWORD)
        response = self.client.post(reverse("profile:api_register"), register_data(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_refuses_duplicate_username_ignoring_case(self):
        User.objects.create_user("Ben", "other@example.com", GOOD_PASSWORD)
        response = self.client.post(reverse("profile:api_register"), register_data(), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_refuses_reserved_usernames(self):
        response = self.client.post(reverse("profile:api_register"), register_data(username="edit"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_logged_in_user_cannot_register_again(self):
        user = User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)
        self.client.force_authenticate(user)
        response = self.client.post(reverse("profile:api_register"), register_data(username="ann", email="a@e.com"), format="json")
        self.assertEqual(response.status_code, 400)


class LoginLogoutAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)

    def test_login_with_right_password(self):
        response = self.client.post(reverse("profile:api_login"), {"username": "ben", "password": GOOD_PASSWORD}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "ben")
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 200)

    def test_login_with_wrong_password(self):
        response = self.client.post(reverse("profile:api_login"), {"username": "ben", "password": "nope"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Wrong username or password", str(response.data["non_field_errors"][0]))
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 403)

    def test_login_with_unknown_username(self):
        response = self.client.post(reverse("profile:api_login"), {"username": "ghost", "password": "x"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not exist", str(response.data["non_field_errors"][0]))

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(reverse("profile:api_login"), {"username": "ben", "password": GOOD_PASSWORD}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_logout_ends_the_session(self):
        self.client.login(username="ben", password=GOOD_PASSWORD)
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 200)
        response = self.client.post(reverse("profile:api_logout"))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 403)

    def test_session_cookie_from_the_website_works_for_the_api(self):
        # logging in on the HTML page also logs in the API, because both use the Django session
        self.client.post(reverse("profile:login"), {"username": "ben", "password": GOOD_PASSWORD})
        self.assertEqual(self.client.get(reverse("profile:api_my_profile")).status_code, 200)


class ProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)
        self.client.force_authenticate(self.user)
        self.url = reverse("profile:api_my_profile")

    def test_my_profile_needs_login(self):
        response = APIClient().get(self.url)
        self.assertIn(response.status_code, (401, 403))

    def test_get_my_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "ben")
        self.assertEqual(response.data["display_name"], "ben")  # username while the display name is empty
        self.assertEqual(response.data["initials"], "B")
        self.assertTrue(response.data["is_owner"])
        self.assertEqual(response.data["stats"]["garden_posts"], 0)

    def test_patch_changes_only_what_is_sent(self):
        plant = Plant.objects.create(name="Test basil", slug="test-basil")
        response = self.client.patch(
            self.url,
            {"display_name": "  Pro   Gardener ", "bio": "Hi", "location": "Jakarta",
             "growing_style": "Rooftop garden", "favorite_plant": plant.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(self.user.first_name, "Pro Gardener")
        self.assertEqual((profile.bio, profile.location, profile.growing_style), ("Hi", "Jakarta", "Rooftop garden"))
        self.assertEqual(response.data["favorite_plant_detail"]["name"], "Test basil")
        # a second PATCH with only the bio leaves the rest alone
        self.client.patch(self.url, {"bio": "New bio"}, format="json")
        profile.refresh_from_db()
        self.assertEqual((profile.bio, profile.location, profile.favorite_plant_id), ("New bio", "Jakarta", plant.id))

    def test_favorite_plant_can_be_cleared_and_unknown_plant_is_refused(self):
        plant = Plant.objects.create(name="Test mint", slug="test-mint")
        self.client.patch(self.url, {"favorite_plant": plant.id}, format="json")
        response = self.client.patch(self.url, {"favorite_plant": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["favorite_plant"])
        self.assertEqual(self.client.patch(self.url, {"favorite_plant": 99999}, format="json").status_code, 400)

    def test_bad_growing_style_and_long_bio_are_refused(self):
        self.assertEqual(self.client.patch(self.url, {"growing_style": "Moon base"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"bio": "x" * 301}, format="json").status_code, 400)

    def test_avatar_color_cannot_be_changed(self):
        color = self.user.profile.avatar_color
        other = "pink" if color != "pink" else "green"
        self.client.patch(self.url, {"avatar_color": other}, format="json")
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.avatar_color, color)

    def test_refuses_http_image_links(self):
        response = self.client.patch(self.url, {"picture_url": "http://example.com/a.jpg"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("picture_url", response.data)

    def test_pasted_https_link_is_saved(self):
        response = self.client.patch(self.url, {"picture_url": "https://example.com/a.jpg"}, format="json")
        self.assertEqual(response.data["profile_picture"], "https://example.com/a.jpg")

    def test_upload_picture_and_serve_it(self):
        photo = SimpleUploadedFile("me.png", PNG, content_type="image/png")
        response = self.client.patch(self.url, {"picture_file": photo}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(ProfileImage.objects.filter(profile__user=self.user, kind="avatar").exists())
        # a full link, pointing at the existing image view
        self.assertTrue(response.data["profile_picture"].startswith("http://testserver/profile/ben/picture/?v="))
        self.assertEqual(self.client.get("/profile/ben/picture/").status_code, 200)

    def test_upload_must_be_a_real_image(self):
        fake = SimpleUploadedFile("me.png", b"not an image", content_type="image/png")
        response = self.client.patch(self.url, {"picture_file": fake}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("picture_file", response.data)

    def test_upload_over_2mb_is_refused(self):
        big = SimpleUploadedFile("me.png", PNG + b"0" * (2 * 1024 * 1024), content_type="image/png")
        self.assertEqual(self.client.patch(self.url, {"picture_file": big}, format="multipart").status_code, 400)

    def test_patch_without_image_keys_keeps_the_upload(self):
        photo = SimpleUploadedFile("me.png", PNG, content_type="image/png")
        self.client.patch(self.url, {"picture_file": photo}, format="multipart")
        self.client.patch(self.url, {"bio": "still here"}, format="json")
        self.assertTrue(ProfileImage.objects.filter(profile__user=self.user, kind="avatar").exists())
        self.assertTrue(self.user.profile.__class__.objects.get(user=self.user).profile_picture.startswith("/profile/ben/picture/"))

    def test_pasted_link_replaces_an_upload_and_remove_clears_it(self):
        photo = SimpleUploadedFile("me.png", PNG, content_type="image/png")
        self.client.patch(self.url, {"banner_file": photo}, format="multipart")
        self.client.patch(self.url, {"banner_url": "https://example.com/b.jpg"}, format="json")
        self.assertFalse(ProfileImage.objects.filter(profile__user=self.user, kind="banner").exists())
        response = self.client.patch(self.url, {"remove_banner": True}, format="json")
        self.assertEqual(response.data["cover_image"], "")

    def test_put_keeps_the_same_rules(self):
        self.assertEqual(self.client.put(self.url, {"bio": "x" * 301}, format="json").status_code, 400)
        self.assertEqual(self.client.put(self.url, {"bio": "ok"}, format="json").status_code, 200)


class PublicProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)
        self.url = reverse("profile:api_profile", args=["ben"])

    def test_anyone_can_read_a_profile_but_not_the_email(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["email"])
        self.assertFalse(response.data["is_owner"])

    def test_another_logged_in_user_does_not_see_the_email_either(self):
        self.client.force_authenticate(User.objects.create_user("ann", "ann@example.com", GOOD_PASSWORD))
        response = self.client.get(self.url)
        self.assertIsNone(response.data["email"])
        self.assertFalse(response.data["is_owner"])

    def test_the_owner_sees_the_email(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.data["email"], "ben@example.com")
        self.assertTrue(response.data["is_owner"])

    def test_unknown_username_is_a_404(self):
        self.assertEqual(self.client.get(reverse("profile:api_profile", args=["ghost"])).status_code, 404)

    def test_visitors_cannot_change_anyone_elses_profile(self):
        # there is no PATCH for /api/profile/<username>/
        self.assertEqual(self.client.patch(self.url, {"bio": "hacked"}, format="json").status_code, 405)


class DeleteAccountAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)
        self.client.force_authenticate(self.user)
        self.url = reverse("profile:api_my_profile")

    def test_wrong_password_keeps_the_account(self):
        response = self.client.delete(self.url, {"password": "nope", "confirm": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="ben").exists())

    def test_must_confirm(self):
        response = self.client.delete(self.url, {"password": GOOD_PASSWORD, "confirm": False}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(username="ben").exists())

    def test_delete_removes_user_and_profile(self):
        response = self.client.delete(self.url, {"password": GOOD_PASSWORD, "confirm": True}, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(username="ben").exists())
        self.assertFalse(Profile.objects.exists())


class CSRFTests(APITestCase):
    def test_logged_in_browser_session_needs_the_csrf_token_to_change_things(self):
        User.objects.create_user("ben", "ben@example.com", GOOD_PASSWORD)
        client = APIClient(enforce_csrf_checks=True)
        client.login(username="ben", password=GOOD_PASSWORD)
        response = client.patch(reverse("profile:api_my_profile"), {"bio": "x"}, format="json")
        self.assertEqual(response.status_code, 403)
