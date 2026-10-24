from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def show_questions(request):
    return render(request, "question_list.html")
    
