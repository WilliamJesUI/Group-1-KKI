from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from .forms import *
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Exists, OuterRef, Count, Case, When, Value, IntegerField
from django.contrib import messages 
from plants.models import Plant


# Create your views here.
QUESTION_FILTERS = [("latest", "Latest"), ("popular", "Popular"), ("unpopular", "Unpopular"), ("mine", "Mine")]
ANSWER_FILTERS = [("most_helpful", "Most Helpful"), ("newest", "Newest"), ("mine", "Mine")]

QUESTION_SORTS = {
    "latest": ["-created_at"],
    "popular": ["-answer_count", "-created_at"],
    "unpopular": ["answer_count", "-created_at"],
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

    question_asked_count = Question.objects.all().count()

    questions = (
        Question.objects
        .select_related("plant", "author__profile")
        .filter(Q(title__icontains=query) | Q(plant__name__icontains=query))
        # distinct=True: with two Counts in one query, each would otherwise count the other's rows too
        .annotate(answer_count=Count("answers", distinct=True), vote_count=Count("voters", distinct=True))
    )


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

    popular_plants = (
        Plant.objects
        .annotate(question_count=Count("questions"))
        .filter(question_count__gt=0)
        .order_by("-question_count", "name")[:5]
    )

    plant_slug = request.GET.get("plant", "").strip()
    if plant_slug:
        questions = questions.filter(plant__slug=plant_slug)

    context = {
        "question_form": QuestionForm(),
        "question_filters": QUESTION_FILTERS,
        "question_list": questions,
        "question_asked_count": question_asked_count,
        "selected_filter": pill,
        "query": query,
        "popular_plants": popular_plants,
        "selected_plant": plant_slug,
        "helpful_answer_count": Answer.objects.annotate(num_voters=Count("voters")).filter(num_voters__gt=0).count()
    }

    if request.GET.get("partial") == "1":
        return render(request, "question_cards.html", context)
    return render(request, "question_list.html", context)

def popular_plants_ajax(request):
    popular_plants = (
            Plant.objects
            .annotate(question_count=Count("questions"))
            .filter(question_count__gt=0)
            .order_by("-question_count", "name")[:5]
        )

    context = {
        "popular_plants" : popular_plants,
        # Keeps the chosen plant highlighted after the box refreshes
        "selected_plant": request.GET.get("plant", "").strip(),
    }
    return render(request, "popular_plants_container.html", context)


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

    # Get related questions
    related_questions = Question.objects.none()
    if question.plant_id:
        related_questions = (
            Question.objects
            .filter(plant_id=question.plant_id)
            .exclude(id=question.id)
            .select_related("plant")
            .annotate(answer_count=Count("answers"))
            .order_by("-created_at")[:5]
        )

    context = {
        "question": question,
        "answer_list": answers,
        "answer_form": AnswerForm(),
        "answer_filters": ANSWER_FILTERS,
        "selected_filter": pill,
        "show_top": pill == "most_helpful",
        "edit_form": QuestionForm(instance=question, auto_id="edit_%s"),
        "related_questions" : related_questions,
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
    first_error = next(iter(form.errors.values()))[0]
    return JsonResponse({"message": first_error, "errors": form.errors.get_json_data()}, status=400)

@require_POST
def update_question_ajax(request, question_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to edit."}, status=403)

    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"message": "Question not found."}, status=404)

    if question.author_id != request.user.id:
        return JsonResponse({"message": "You can only edit your own questions."}, status=403)

    if question.answers.exists():
        return JsonResponse(
            {"message": "This question already has answers, so it can't be edited."},
            status=409,
        )

    form = QuestionForm(request.POST, instance=question)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse(
            {"message": first_error, "errors": form.errors.get_json_data()},
            status=400,
        )

    form.save()
    messages.success(request, "Question updated\nYour changes are saved.")
    return JsonResponse({"url": reverse("community:show_question_thread", args=[question.id])})


@require_POST
def delete_question_ajax(request, question_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to delete."}, status=403)

    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return JsonResponse({"message": "Question not found."}, status=404)

    if question.author_id != request.user.id:
        return JsonResponse({"message": "You can only delete your own questions."}, status=403)

    if question.answers.count() > 0:
        return JsonResponse(
            {"message": "This question already has answers, so it can't be deleted."},
            status=409,
        )

    question.delete()
    messages.success(request, "Question deleted\nIt has been removed from the community.")
    return JsonResponse({"url": reverse("community:show_questions")})


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
        return JsonResponse({"message" : "Please log in to answer!"}, status=403)

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
    first_error = next(iter(form.errors.values()))[0]
    return JsonResponse({"message": first_error, "errors": form.errors.get_json_data()}, status=400)


@require_POST
def update_answer_ajax(request, answer_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to edit."}, status=403)

    try:
        answer = Answer.objects.get(id=answer_id)
    except Answer.DoesNotExist:
        return JsonResponse({"message": "Answer not found."}, status=404)

    if answer.author_id != request.user.id:
        return JsonResponse({"message": "You can only edit your own answers."}, status=403)

    form = AnswerForm(request.POST, instance=answer)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse({"message": first_error, "errors": form.errors.get_json_data()}, status=400)

    form.save()
    return JsonResponse({"id": answer.id})

@require_POST
def delete_answer_ajax(request, answer_id):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Please log in to delete."}, status=403)

    try:
        answer = Answer.objects.get(id=answer_id)
    except Answer.DoesNotExist:
        return JsonResponse({"message": "Answer not found."}, status=404)

    if answer.author_id != request.user.id:
        return JsonResponse({"message": "You can only delete your own answers."}, status=403)

    answer.delete()
    return JsonResponse({"id": answer_id})

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

def save_question_from_form(question, form):
    question.title = form.cleaned_data["title"]
    question.body = form.cleaned_data["body"]
    question.save()

def save_answer_from_form(answer, form):
    answer.body = form.cleaned_data["body"]
    answer.save()
    
