from django.db.models import Case, Count, IntegerField, Q, Value, When
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Question
from .serializers import QuestionSerializer

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


@api_view(["GET", "HEAD", "POST"])
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

def answers_for_question(request, question_id):
    pass