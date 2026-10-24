from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from .forms import *
from django.views.decorators.http import require_POST

# Create your views here.
def show_questions(request):
    context = {
        "question_form" : QuestionForm(),
        "question_list" : Question.objects.all(),
    }

    return render(request, "question_list.html", context)

def show_question(request, question_id):
    question = Question.objects.all().get(id=question_id)

    return HttpResponse(f"{question.title} {question.body}")

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
        
    
