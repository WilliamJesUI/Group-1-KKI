from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Question, Answer
from plants.models import Plant

from django.db.models import Count, Q, When, Case, Value, IntegerField
from .serializers import AnswerSerializer, QuestionSerializer
from .permissions import IsAuthorOrReadOnly

QUESTION_FILTERS = [("latest", "Latest"), ("popular", "Popular"), ("unpopular", "Unpopular"), ("mine", "Mine")]
QUESTION_SORTS = {
    "latest": ["-created_at"],
    "popular": ["-answer_count", "-created_at"],
    "unpopular": ["answer_count", "-created_at"],
    "mine" : ["-created_at"],
}

ANSWER_FILTERS = [("most_helpful", "Most Helpful"), ("newest", "Newest"), ("mine", "Mine")]
ANSWER_SORTS = {
    "most_helpful": ["-vote_count", "-created_at"],
    "newest": ["-created_at"],
    "mine": ["-created_at"],
}

@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthorOrReadOnly])
def question_list(request):
    if request.method in ("GET", "HEAD"):
        query = request.GET.get("q", "").strip()
        pill = request.GET.get("filter", "latest")

        # If pill not found, then fall back to the default
        pill = "latest" if pill not in QUESTION_SORTS else pill

        # "mine" needs a logged-in user, otherwise fall back to the default
        pill = "latest" if pill == "mine" and not request.user.is_authenticated else pill

        questions = (
            Question.objects
            .select_related("plant", "author__profile")
            .prefetch_related("voters")
            .filter(Q(title__icontains=query) | Q(plant__name__icontains=query))
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

        plant_filter = request.query_params.get("plant")
        if plant_filter:
            questions = questions.filter(plant__slug=plant_filter)

        serializer = QuestionSerializer(questions, many=True, context={"request": request})
        return Response(serializer.data)

    serializer = QuestionSerializer(data=request.data, context={"request":request})
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthorOrReadOnly])
def answer_list(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method in ("GET", "HEAD"):
        pill = request.GET.get("filter", "most_helpful")

        pill = "most_helpful" if pill not in ANSWER_SORTS else pill
        pill = "most_helpful" if pill == "mine" and not request.user.is_authenticated else pill

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

        serializer = AnswerSerializer(answers, many=True, context={"request": request})
        return Response(serializer.data)
    
    serializer = AnswerSerializer(data=request.data, context={"request":request})
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user, question=question)
    return Response(serializer.data, status=status.HTTP_201_CREATED)