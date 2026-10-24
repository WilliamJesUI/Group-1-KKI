from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from .forms import *
from django.views.decorators.http import require_POST
from django.db.models import Count, Q

# Create your views here.
QUESTION_FILTERS = [("latest", "Latest"), ("popular", "Popular"), ("unanswered", "Unanswered")]
SORTS = {
    "latest": ["-created_at"],
    "popular": ["-answer_count", "-created_at"],
    "unanswered": ["-created_at"],
}
def show_questions(request):
    query = request.GET.get("q", "").strip()
    pill = request.GET.get("filter", "latest")
    if pill not in SORTS:
        pill = "latest"

    questions = (
        Question.objects
        .filter(title__icontains=query)
        .annotate(answer_count=Count("answers"))
    )
    if pill == "unanswered":
        questions = questions.filter(answer_count=0)
    questions = questions.order_by(*SORTS[pill])

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
    question = Question.objects.all().get(id=question_id)

    context = {
        "question" : question,
        "answer_list" : question.answers.all(),
        "answer_form" : AnswerForm(),
    }

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
        return JsonResponse({"url" : reverse("community:show_questions", args=[question.id])}, status=201)
    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


def save_question_from_form(question, form):
    question.title = form.cleaned_data["title"]
    question.body = form.cleaned_data["body"]
    question.created_at = form.cleaned_data["created_at"]
    question.updated_at = form.cleaned_data["updated_at"]
    question.save()
        
    
