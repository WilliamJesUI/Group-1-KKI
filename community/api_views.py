from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import Question, Answer
from .serializers import AnswerSerializer, QuestionSerializer
from .permissions import IsAuthorOrReadOnly

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


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthorOrReadOnly])
def question_detail(request, question_id):
    question = get_object_or_404(
        Question.objects.prefetch_related("voters"), id=question_id
    )

    permission = IsAuthorOrReadOnly()
    if not permission.has_object_permission(request, None, question):
        raise PermissionDenied(permission.message)


    if request.method in ("GET", "HEAD"):
        serializer = QuestionSerializer(question, context={"request":request})
        return Response(serializer.data)

    if request.method in ("PUT", "PATCH") and question.answers.exists():
        return Response(
            {"detail": "This question already has answers, so it can't be edited."},
            status=status.HTTP_409_CONFLICT,
        )

    if request.method == "DELETE":
        if not question.answers.exists():
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "This question already has answers, so it can't be deleted."}, status=status.HTTP_409_CONFLICT)

    serializer = QuestionSerializer(
        question, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)

@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthorOrReadOnly])
def question_list(request):
    if request.method in ("GET", "HEAD"):
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

        plant_slug = request.GET.get("plant", "").strip()
        if plant_slug:
            questions = questions.filter(plant__slug=plant_slug)

        serializer = QuestionSerializer(
            questions, many=True, context={"request": request},
        )
        return Response(serializer.data)

    serializer = QuestionSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET", "HEAD", "POST"])
@permission_classes([IsAuthorOrReadOnly])
def answers_for_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method in ("GET", "HEAD"):
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
        serializer = AnswerSerializer(
            answers, many=True, context={"request": request},
        )
        return Response(serializer.data)

    serializer = AnswerSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user, question=question)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthorOrReadOnly])
def answer_detail(request, answer_id):
    answer = get_object_or_404(
        Answer.objects.prefetch_related("voters"), id=answer_id
    )

    permission = IsAuthorOrReadOnly()
    if not permission.has_object_permission(request, None, answer):
        raise PermissionDenied(permission.message)

    if request.method in ("GET", "HEAD"):
        serializer = AnswerSerializer(answer, context={"request":request})
        return Response(serializer.data)

    if request.method == "DELETE":
        answer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = AnswerSerializer(
        answer, data=request.data, partial=request.method == "PATCH",
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)



# Toggling logic
def toggle_vote(obj, user):
    if obj.voters.filter(id=user.id).exists():
        obj.voters.remove(user)
        voted = False
    else:
        obj.voters.add(user)
        voted = True
    return {"voted": voted, "vote_count": obj.voters.count()}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question_vote(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    return Response(toggle_vote(question, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer_vote(request, answer_id):
    answer = get_object_or_404(Answer, id=answer_id)
    return Response(toggle_vote(answer, request.user))
