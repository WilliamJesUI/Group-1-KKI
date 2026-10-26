from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from .forms import *
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Exists, OuterRef, Count, Case, When, Value, IntegerField


# Create your views here.
QUESTION_FILTERS = [("latest", "Latest"), ("popular", "Popular"), ("unanswered", "Unanswered"), ("mine", "Mine")]
ANSWER_FILTERS = [("most_helpful", "Most Helpful"), ("newest", "Newest"), ("mine", "Mine")]

QUESTION_SORTS = {
    "latest": ["-created_at"],
    "popular": ["-answer_count", "-created_at"],
    "unanswered": ["-created_at"],
    "mine" : ["-created_at"],
}
ANSWER_SORTS = {
    "most_helpful": ["-vote_count", "-created_at"],
    "newest": ["-created_at"],
    "mine": ["-created_at"],
}


def show_questions(request):
    query = request.GET.get("q", "").strip()
    pill = request.GET.get("filter", "latest")
    if pill not in QUESTION_SORTS:
        pill = "latest"

    # "mine" needs a logged-in user, otherwise fall back to the default
    if pill == "mine" and not request.user.is_authenticated:
        pill = "latest"

    questions = (
        Question.objects
        .filter(title__icontains=query)
        .annotate(answer_count=Count("answers"))
    )

    if pill == "unanswered":
        questions = questions.filter(answer_count=0)

    order = list(QUESTION_SORTS[pill])

    if pill == "mine":
        questions = questions.annotate(
            mine_rank=Case(
                When(author=request.user, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        order.insert(0, "mine_rank")   # my questions first, then newest

    questions = questions.order_by(*order)

    context = {
        "question_form": QuestionForm(),
        "question_filters": QUESTION_FILTERS,
        "question_list": questions,
        "selected_filter": pill,
        "query": query,
    }

    if request.GET.get("partial") == "1":
        return render(request, "question_cards.html", context)
    return render(request, "question_list.html", context)

def show_question_thread(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    pill = request.GET.get("filter", "most_helpful")
    if pill not in ANSWER_SORTS:
        pill = "most_helpful"

    if pill == "mine" and not request.user.is_authenticated:
        pill = "most_helpful"

    answers = (
        question.answers
        .select_related("author")
        .prefetch_related("voters")
        .annotate(vote_count=Count("voters"))
    )

    order = list(ANSWER_SORTS[pill])

    if pill == "mine":
        answers = answers.annotate(
            mine_rank=Case(
                When(author=request.user, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        order.insert(0, "mine_rank")   # my answers first, then the rest

    answers = answers.order_by(*order)

    context = {
        "question": question,
        "answer_list": answers,
        "answer_form": AnswerForm(),
        "answer_filters": ANSWER_FILTERS,
        "selected_filter": pill,
        "show_top": pill == "most_helpful",
    }

    if request.GET.get("partial") == "1":
        return render(request, "answer_cards.html", context)
    return render(request, "question_thread.html", context)

@require_POST
def create_question_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to ask a question!"}, status=403)

    form = QuestionForm(request.POST)
    if form.is_valid():
        question = form.save(commit=False)
        question.author = request.user
        save_question_from_form(question, form)
        return JsonResponse({"url" : reverse("community:show_questions")}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def vote_question_ajax(request, question_id):
    if not request.user.is_authenticated:
            return JsonResponse({"message": "Please log in to vote!"}, status=403)
    try:
        question = Question.objects.all().get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"message": "Question not found."}, status=404)

    if question.voters.filter(id=request.user.id).exists():
        question.voters.remove(request.user)
        voted = False
    else:
        question.voters.add(request.user)
        voted = True

    return JsonResponse({"message":"Voted successfully!", "voted":voted,"score":str(question.voters.count()),}, status=201)

@require_POST
def create_answer_ajax(request, question_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message" : "Please log in to ask a question!"}, status=403)

    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"message": "Question not found."}, status=404)

    form = AnswerForm(request.POST)
    if form.is_valid():
        answer = form.save(commit=False)
        answer.author = request.user
        answer.question = question
        save_answer_from_form(answer, form)
        return JsonResponse({"url" : reverse("community:show_question_thread", args=[question.id])}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


@require_POST
def vote_answer_ajax(request, answer_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to vote!"}, status=403)

    try:
        answer = Answer.objects.get(id=answer_id)
    except Answer.DoesNotExist:
        return JsonResponse({"message": "Answer not found."}, status=404)

    if answer.voters.filter(id=request.user.id).exists():
        answer.voters.remove(request.user)
        voted = False
    else:
        answer.voters.add(request.user)
        voted = True

    return JsonResponse({"voted": voted, "score": answer.voters.count()})

@require_POST
def unvote_answer_ajax(request, answer_id):
    if not request.user.is_authenticated:
        return JsonResponse


def save_question_from_form(question, form):
    question.title = form.cleaned_data["title"]
    question.body = form.cleaned_data["body"]
    question.save()

def save_answer_from_form(answer, form):
    answer.body = form.cleaned_data["body"]
    answer.save()
        
    
