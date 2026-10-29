from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from plants.models import Plant

from .forms import AnswerForm, QuestionForm
from .models import Answer, Question


class CommunityTestCase(TestCase):
    # Shared setup: two users, two plants, one question each
    def setUp(self):
        self.ben = User.objects.create_user(username="ben", password="pass12345")
        self.ala = User.objects.create_user(username="ala", password="pass12345")
        self.basil = Plant.objects.create(name="Test basil", slug="test-basil", category="herbs")
        self.tomato = Plant.objects.create(name="Test tomato", slug="test-tomato", category="vegetables")
        self.basil_question = Question.objects.create(
            author=self.ben, title="Why is my basil yellow?", body="Leaves turn yellow", plant=self.basil
        )
        self.tomato_question = Question.objects.create(
            author=self.ala, title="Tomato watering", body="How often?", plant=self.tomato
        )

    def login(self, user):
        self.client.login(username=user.username, password="pass12345")

    def titles(self, response):
        return [q.title for q in response.context["question_list"]]


class ModelTest(CommunityTestCase):
    def test_question_str_has_title(self):
        self.assertIn("Why is my basil yellow?", str(self.basil_question))

    def test_deleting_plant_keeps_question(self):
        # plant uses SET_NULL, so the question stays without a tag
        self.basil.delete()
        self.basil_question.refresh_from_db()
        self.assertIsNone(self.basil_question.plant)


class FormTest(CommunityTestCase):
    def test_question_form_needs_title(self):
        form = QuestionForm(data={"title": "", "body": "x"})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_question_form_plant_is_optional(self):
        self.assertTrue(QuestionForm(data={"title": "Hi", "body": ""}).is_valid())

    def test_answer_form_needs_body(self):
        self.assertFalse(AnswerForm(data={"body": ""}).is_valid())


class QuestionListTest(CommunityTestCase):
    url = reverse("community:show_questions")

    def test_page_loads_with_all_questions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "question_list.html")
        self.assertEqual(len(self.titles(response)), 2)
        self.assertEqual(response.context["question_asked_count"], 2)

    def test_partial_returns_only_the_cards(self):
        response = self.client.get(self.url, {"partial": "1"})
        self.assertTemplateUsed(response, "question_cards.html")
        self.assertTemplateNotUsed(response, "question_list.html")

    def test_search_matches_title(self):
        response = self.client.get(self.url, {"q": "watering"})
        self.assertEqual(self.titles(response), ["Tomato watering"])

    def test_search_matches_plant_name(self):
        response = self.client.get(self.url, {"q": "basil"})
        self.assertEqual(self.titles(response), ["Why is my basil yellow?"])

    def test_plant_filter(self):
        response = self.client.get(self.url, {"plant": "test-tomato"})
        self.assertEqual(self.titles(response), ["Tomato watering"])
        self.assertEqual(response.context["selected_plant"], "test-tomato")

    def test_plant_filter_and_search_together(self):
        response = self.client.get(self.url, {"plant": "test-basil", "q": "watering"})
        self.assertEqual(self.titles(response), [])

    def test_popular_plant_links_use_the_plant_filter(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'href="?plant=test-basil"')

    def test_popular_sorts_by_answer_count(self):
        Answer.objects.create(question=self.tomato_question, author=self.ben, body="Every 2 days")
        response = self.client.get(self.url, {"filter": "popular"})
        self.assertEqual(self.titles(response)[0], "Tomato watering")

    def test_unpopular_sorts_fewest_answers_first(self):
        Answer.objects.create(question=self.tomato_question, author=self.ben, body="Every 2 days")
        response = self.client.get(self.url, {"filter": "unpopular"})
        self.assertEqual(self.titles(response)[0], "Why is my basil yellow?")

    def test_unknown_filter_falls_back_to_latest(self):
        response = self.client.get(self.url, {"filter": "nope"})
        self.assertEqual(response.context["selected_filter"], "latest")

    def test_mine_needs_login(self):
        response = self.client.get(self.url, {"filter": "mine"})
        self.assertEqual(response.context["selected_filter"], "latest")

    def test_counts_are_correct_with_votes_and_answers(self):
        # two Counts in one query: without distinct=True these numbers would multiply
        self.tomato_question.voters.add(self.ben, self.ala)
        Answer.objects.create(question=self.tomato_question, author=self.ben, body="A")
        Answer.objects.create(question=self.tomato_question, author=self.ala, body="B")
        Answer.objects.create(question=self.tomato_question, author=self.ala, body="C")
        response = self.client.get(self.url)
        question = next(q for q in response.context["question_list"] if q.pk == self.tomato_question.pk)
        self.assertEqual((question.answer_count, question.vote_count), (3, 2))

    def test_query_count_does_not_grow_with_more_questions(self):
        for i in range(10):
            Question.objects.create(author=self.ben, title=f"Extra {i}")
        # 12 cards, but the same handful of queries as for 2 cards
        with self.assertNumQueries(5):
            self.client.get(self.url)

    def test_mine_puts_my_questions_first(self):
        self.login(self.ben)
        response = self.client.get(self.url, {"filter": "mine"})
        self.assertEqual(self.titles(response)[0], "Why is my basil yellow?")

class PopularPlantsBoxTest(CommunityTestCase):
    """The Popular Plants box that community_popular_plants.js refreshes after a new question."""

    def setUp(self):
        super().setUp()
        self.url = reverse("community:popular_plants_ajax")

    def test_shows_at_most_five_plants_like_the_page(self):
        for number in range(6):
            plant = Plant.objects.create(name=f"Plant {number}", slug=f"plant-{number}")
            Question.objects.create(author=self.ben, title=f"Q {number}", plant=plant)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["popular_plants"]), 5)

    def test_keeps_the_chosen_plant_highlighted(self):
        response = self.client.get(self.url, {"plant": "test-basil"})
        self.assertEqual(response.context["selected_plant"], "test-basil")
        self.assertContains(response, 'data-plant="test-basil"')
        self.assertContains(response, 'aria-current="true"')

    def test_uses_small_photos(self):
        self.basil.image_url = "https://bs.plantnet.org/image/o/abc"
        self.basil.save()
        response = self.client.get(self.url)
        self.assertContains(response, "https://bs.plantnet.org/image/s/abc")
        self.assertNotContains(response, "/image/o/abc")



class QuestionThreadTest(CommunityTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("community:show_question_thread", args=[self.basil_question.id])
        self.old = Answer.objects.create(question=self.basil_question, author=self.ala, body="Too much water")
        self.new = Answer.objects.create(question=self.basil_question, author=self.ben, body="Needs sun")
        self.old.voters.add(self.ala)

    def answers(self, response):
        return [a.body for a in response.context["answer_list"]]

    def test_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "question_thread.html")

    def test_missing_question_is_404(self):
        response = self.client.get(reverse("community:show_question_thread", args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_most_helpful_first_by_default(self):
        response = self.client.get(self.url)
        self.assertEqual(self.answers(response)[0], "Too much water")
        self.assertTrue(response.context["show_top"])

    def test_newest_filter(self):
        response = self.client.get(self.url, {"filter": "newest"})
        self.assertEqual(self.answers(response)[0], "Needs sun")

    def test_unknown_filter_falls_back(self):
        response = self.client.get(self.url, {"filter": "nope"})
        self.assertEqual(response.context["selected_filter"], "most_helpful")

    def test_mine_needs_login(self):
        response = self.client.get(self.url, {"filter": "mine"})
        self.assertEqual(response.context["selected_filter"], "most_helpful")

    def test_mine_puts_my_answers_first(self):
        self.login(self.ben)
        response = self.client.get(self.url, {"filter": "mine"})
        self.assertEqual(self.answers(response)[0], "Needs sun")

    def test_partial_returns_only_the_answers(self):
        response = self.client.get(self.url, {"partial": "1"})
        self.assertTemplateUsed(response, "answer_cards.html")
        self.assertTemplateNotUsed(response, "question_thread.html")

    def test_related_questions_share_the_plant(self):
        other = Question.objects.create(author=self.ala, title="Basil flowers", plant=self.basil)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context["related_questions"]), [other])

    def test_no_related_questions_without_plant(self):
        untagged = Question.objects.create(author=self.ala, title="General tip")
        response = self.client.get(reverse("community:show_question_thread", args=[untagged.id]))
        self.assertEqual(list(response.context["related_questions"]), [])


class CreateQuestionTest(CommunityTestCase):
    url = reverse("community:create_question_ajax")

    def test_logged_out_gets_403(self):
        response = self.client.post(self.url, {"title": "Hi"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("log in", response.json()["message"])

    def test_creates_question_with_plant(self):
        self.login(self.ben)
        response = self.client.post(self.url, {"title": "New one", "body": "Help", "plant": self.basil.pk})
        self.assertEqual(response.status_code, 201)
        question = Question.objects.get(title="New one")
        self.assertEqual(question.author, self.ben)
        self.assertEqual(question.plant, self.basil)

    def test_invalid_form_gets_400(self):
        self.login(self.ben)
        response = self.client.post(self.url, {"title": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.json()["errors"])
        self.assertEqual(response.json()["message"], "This field is required.")

    def test_get_is_not_allowed(self):
        self.login(self.ben)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class UpdateQuestionTest(CommunityTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("community:update_question_ajax", args=[self.basil_question.id])

    def test_logged_out_gets_403(self):
        self.assertEqual(self.client.post(self.url, {"title": "x"}).status_code, 403)

    def test_missing_question_is_404(self):
        self.login(self.ben)
        response = self.client.post(reverse("community:update_question_ajax", args=[999]), {"title": "x"})
        self.assertEqual(response.status_code, 404)

    def test_only_author_can_edit(self):
        self.login(self.ala)
        response = self.client.post(self.url, {"title": "Hacked"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("your own", response.json()["message"])
        self.basil_question.refresh_from_db()
        self.assertEqual(self.basil_question.title, "Why is my basil yellow?")

    def test_answered_question_cannot_be_edited(self):
        Answer.objects.create(question=self.basil_question, author=self.ala, body="Water less")
        self.login(self.ben)
        self.assertEqual(self.client.post(self.url, {"title": "Changed"}).status_code, 409)

    def test_invalid_form_gets_400_with_message(self):
        self.login(self.ben)
        response = self.client.post(self.url, {"title": ""})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["message"])

    def test_author_can_edit(self):
        self.login(self.ben)
        response = self.client.post(self.url, {"title": "Basil help", "body": "New", "plant": self.tomato.pk})
        self.assertEqual(response.status_code, 200)
        self.basil_question.refresh_from_db()
        self.assertEqual(self.basil_question.title, "Basil help")
        self.assertEqual(self.basil_question.plant, self.tomato)


class DeleteQuestionTest(CommunityTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("community:delete_question_ajax", args=[self.basil_question.id])

    def test_logged_out_gets_403(self):
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_missing_question_is_404(self):
        self.login(self.ben)
        self.assertEqual(self.client.post(reverse("community:delete_question_ajax", args=[999])).status_code, 404)

    def test_only_author_can_delete(self):
        self.login(self.ala)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Question.objects.filter(pk=self.basil_question.pk).exists())

    def test_answered_question_cannot_be_deleted(self):
        Answer.objects.create(question=self.basil_question, author=self.ala, body="Water less")
        self.login(self.ben)
        self.assertEqual(self.client.post(self.url).status_code, 409)

    def test_author_can_delete(self):
        self.login(self.ben)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], reverse("community:show_questions"))
        self.assertFalse(Question.objects.filter(pk=self.basil_question.pk).exists())


class VoteTest(CommunityTestCase):
    def setUp(self):
        super().setUp()
        self.answer = Answer.objects.create(question=self.basil_question, author=self.ala, body="Water less")
        self.question_url = reverse("community:vote_question_ajax", args=[self.basil_question.id])
        self.answer_url = reverse("community:vote_answer_ajax", args=[self.answer.id])

    def test_logged_out_cannot_vote(self):
        self.assertEqual(self.client.post(self.question_url).status_code, 403)
        self.assertEqual(self.client.post(self.answer_url).status_code, 403)

    def test_missing_items_are_404(self):
        self.login(self.ben)
        self.assertEqual(self.client.post(reverse("community:vote_question_ajax", args=[999])).status_code, 404)
        self.assertEqual(self.client.post(reverse("community:vote_answer_ajax", args=[999])).status_code, 404)

    def test_question_vote_toggles(self):
        self.login(self.ben)
        first = self.client.post(self.question_url).json()
        self.assertEqual((first["voted"], first["score"]), (True, "1"))
        second = self.client.post(self.question_url).json()
        self.assertEqual((second["voted"], second["score"]), (False, "0"))

    def test_answer_vote_toggles(self):
        self.login(self.ben)
        first = self.client.post(self.answer_url).json()
        self.assertEqual((first["voted"], first["score"]), (True, 1))
        second = self.client.post(self.answer_url).json()
        self.assertEqual((second["voted"], second["score"]), (False, 0))


class AnswerTest(CommunityTestCase):
    def setUp(self):
        super().setUp()
        self.answer = Answer.objects.create(question=self.basil_question, author=self.ala, body="Water less")
        self.create_url = reverse("community:create_answer_ajax", args=[self.basil_question.id])
        self.update_url = reverse("community:update_answer_ajax", args=[self.answer.id])
        self.delete_url = reverse("community:delete_answer_ajax", args=[self.answer.id])

    def test_logged_out_cannot_answer_edit_or_delete(self):
        self.assertEqual(self.client.post(self.create_url, {"body": "Hi"}).status_code, 403)
        self.assertEqual(self.client.post(self.update_url, {"body": "Hi"}).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)

    def test_create_answer(self):
        self.login(self.ben)
        response = self.client.post(self.create_url, {"body": "More sun"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Answer.objects.filter(body="More sun", author=self.ben, question=self.basil_question).exists())

    def test_create_answer_on_missing_question_is_404(self):
        self.login(self.ben)
        response = self.client.post(reverse("community:create_answer_ajax", args=[999]), {"body": "Hi"})
        self.assertEqual(response.status_code, 404)

    def test_empty_answer_gets_400(self):
        self.login(self.ben)
        self.assertEqual(self.client.post(self.create_url, {"body": ""}).status_code, 400)

    def test_missing_answer_is_404(self):
        self.login(self.ala)
        self.assertEqual(self.client.post(reverse("community:update_answer_ajax", args=[999]), {"body": "x"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("community:delete_answer_ajax", args=[999])).status_code, 404)

    def test_only_author_can_edit_or_delete(self):
        self.login(self.ben)
        self.assertEqual(self.client.post(self.update_url, {"body": "Hacked"}).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.body, "Water less")

    def test_edit_with_empty_body_gets_400(self):
        self.login(self.ala)
        response = self.client.post(self.update_url, {"body": ""})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["message"])

    def test_author_can_edit(self):
        self.login(self.ala)
        response = self.client.post(self.update_url, {"body": "Water a lot less"})
        self.assertEqual(response.status_code, 200)
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.body, "Water a lot less")

    def test_author_can_delete(self):
        self.login(self.ala)
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Answer.objects.filter(pk=self.answer.pk).exists())

        
class PlantTagLinkTest(CommunityTestCase):
    """The plant tag on a question opens that plant's page in the Encyclopedia, like on Events."""

    def test_question_card_tag_links_to_plant_page(self):
        response = self.client.get(reverse("community:show_questions"))
        self.assertContains(response, 'href="/encyclopedia/test-basil/"')

    def test_question_page_tag_links_to_plant_page(self):
        response = self.client.get(reverse("community:show_question_thread", args=[self.basil_question.id]))
        self.assertContains(response, 'href="/encyclopedia/test-basil/"')