from datetime import date

from django.db.models import Count, Exists, OuterRef
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from events.models import Event
from garden.forms import CommentForm, PlantOfTheWeekForm, PostForm
from garden.models import Comment, PlantOfTheWeek, Post
from growyourgarden.permissions import ajax_login_required, ajax_moderator_required, can_delete, is_moderator
from plants.models import Plant

# The filter pills above the feed (Figma): (value in the URL, label on the pill).
# The plant categories come from the shared Plant table, so a post's category is its plant's category.
GARDEN_FILTERS = [("all", "All plants"), ("vegetables", "Vegetables"), ("herbs", "Herbs"), ("flowers", "Flowers"), ("mine", "My posts")]

# How many comments show when the comments open (Figma "Post Card / comments open")
COMMENT_PREVIEW_COUNT = 3


def posts_for(user):
    """All posts with everything the cards need, in a fixed number of queries (no extra query per card)."""
    posts = (
        Post.objects.defer("photo")  # the cards only need the photo URL, not the photo bytes
        .select_related("author__profile", "plant")
        .annotate(like_count=Count("likes", distinct=True), comment_count=Count("comments", distinct=True))
    )
    if user.is_authenticated:
        # Exists(...) adds a True/False "did this user like it" to each post inside the same query
        posts = posts.annotate(is_liked=Exists(Post.likes.through.objects.filter(post=OuterRef("pk"), user=user)))
    return posts


def mark_permissions(posts, user):
    # What the ••• menu shows on each card (Figma B): Edit for the author, Delete for the author and moderators
    for post in posts:
        post.can_edit = user.is_authenticated and post.author_id == user.pk
        post.can_delete = can_delete(user, post.author)
    return posts


def filter_posts(posts, selected_filter, user):
    if selected_filter == "mine":
        return posts.filter(author=user) if user.is_authenticated else posts.none()
    if selected_filter in ("vegetables", "herbs", "flowers"):
        return posts.filter(plant__category=selected_filter)
    return posts


def get_plant_of_the_week():
    """The newest admin pick. Without one, a plant with a photo picked by the week number,
    so it changes every week by itself. Returns (plant, short_line) or (None, "")."""
    pick = PlantOfTheWeek.objects.select_related("plant").first()
    if pick:
        return pick.plant, pick.short_line
    plants = Plant.objects.exclude(image_url="").order_by("pk")
    count = plants.count()
    if not count:
        return None, ""
    week_number = date.today().isocalendar().week
    return plants[week_number % count], ""


def plant_of_the_week_context(user):
    plant, short_line = get_plant_of_the_week()
    context = {"week_plant": plant, "week_short_line": short_line}
    if is_moderator(user):
        # The admin pop-up, already filled in with the current plant
        context["week_form"] = PlantOfTheWeekForm(initial={"plant": plant, "short_line": short_line})
    return context


def render_card(request, post):
    # One post card as HTML, for garden.js to put into the page after create or edit
    post = mark_permissions([posts_for(request.user).get(pk=post.pk)], request.user)[0]
    return render_to_string("garden/post_card.html", {"post": post, "user": request.user}, request=request)


# ensure_csrf_cookie: likes and comments use fetch, which needs the csrftoken cookie
@ensure_csrf_cookie
def show_garden(request):
    # ?filter=herbs picks a pill. Anything unknown falls back to All plants.
    selected_filter = request.GET.get("filter", "all")
    if selected_filter not in dict(GARDEN_FILTERS):
        selected_filter = "all"
    posts = filter_posts(posts_for(request.user), selected_filter, request.user)
    # ?plant=sweet-basil shows only posts about that plant (the plant tag and the plant page link here)
    plant_slug = request.GET.get("plant", "").strip()
    selected_plant = Plant.objects.filter(slug=plant_slug).first() if plant_slug else None
    if selected_plant:
        posts = posts.filter(plant=selected_plant)
    posts = mark_permissions(list(posts), request.user)

    context = {"posts": posts, "selected_filter": selected_filter, "selected_plant": selected_plant}
    # ?partial=1 comes from garden.js: send only the feed, it swaps it into the page
    if request.GET.get("partial") == "1":
        return render(request, "garden/post_feed.html", context)

    context.update({
        "garden_filters": GARDEN_FILTERS,
        "upcoming_events": Event.objects.defer("cover_image").filter(start_time__gte=timezone.now()).order_by("start_time")[:3],
        "form": PostForm(),
        "comment_form": CommentForm(),
        **plant_of_the_week_context(request.user),
    })
    return render(request, "garden/garden.html", context)


def show_post_photo(request, post_id):
    # Sends the uploaded photo from the database to the browser, like a normal image file
    post = get_object_or_404(Post, pk=post_id)
    if not post.photo_type:
        raise Http404("This post has no uploaded photo.")
    response = HttpResponse(bytes(post.photo), content_type=post.photo_type)
    # The browser keeps it for a day. Editing the post changes the ?v= in its URL, so a new photo loads again.
    response["Cache-Control"] = "public, max-age=86400"
    return response


def save_post_from_form(post, form):
    # Used by both create and edit: the photo is saved by hand, because it isn't a normal model field
    photo = form.cleaned_data["photo_upload"]
    if photo:
        post.photo = photo["data"]
        post.photo_type = photo["type"]
        post.image_url = ""
    elif form.cleaned_data["remove_photo"]:
        post.photo = None
        post.photo_type = ""
        post.image_url = ""
    post.save()


@require_POST
@ajax_login_required("Please log in to share a post.")
def create_post(request):
    form = PostForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    post = form.save(commit=False)
    post.author = request.user
    save_post_from_form(post, form)
    return JsonResponse({"html": render_card(request, post)}, status=201)


@require_POST
@ajax_login_required("Please log in to edit this post.")
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    # Only the author edits. Moderators can delete, but not change someone else's words.
    if post.author != request.user:
        return JsonResponse({"message": "You can only edit your own posts."}, status=403)
    form = PostForm(request.POST, request.FILES, instance=post)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    save_post_from_form(form.save(commit=False), form)
    return JsonResponse({"html": render_card(request, post)})


@require_POST
@ajax_login_required("Please log in to delete this post.")
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not can_delete(request.user, post.author):
        return JsonResponse({"message": "You can only delete your own posts."}, status=403)
    post.delete()
    return JsonResponse({"deleted": True})


@require_POST
@ajax_login_required("Please log in to like posts.")
def like_post(request, post_id):
    post = get_object_or_404(Post.objects.defer("photo"), pk=post_id)
    # The button sends what the user wants (liked=true or false) instead of "flip it",
    # so double clicks or two open tabs can't undo a like by accident. Same idea as the RSVP button.
    if request.POST.get("liked") == "true":
        post.likes.add(request.user)
    else:
        post.likes.remove(request.user)
    return JsonResponse({
        "liked": post.likes.filter(pk=request.user.pk).exists(),
        "like_count": post.likes.count(),
    })


def comment_context(request, post, comments):
    for comment in comments:
        comment.can_delete = can_delete(request.user, comment.author)
    return {"post": post, "comments": comments, "user": request.user}


@require_GET
def show_comments(request, post_id):
    # Opening the comments (Figma A): the newest 3, or all of them with ?all=1
    post = get_object_or_404(Post.objects.defer("photo"), pk=post_id)
    comments = post.comments.select_related("author__profile")
    total = comments.count()
    if request.GET.get("all") != "1" and total > COMMENT_PREVIEW_COUNT:
        # The newest 3, still shown oldest first so they read like a conversation
        comments = list(comments.order_by("-created_at")[:COMMENT_PREVIEW_COUNT])[::-1]
        hidden_count = total - COMMENT_PREVIEW_COUNT
    else:
        comments = list(comments)
        hidden_count = 0
    context = comment_context(request, post, comments)
    context["hidden_count"] = hidden_count
    return render(request, "garden/comment_list.html", context)


@require_POST
@ajax_login_required("Please log in to comment.")
def add_comment(request, post_id):
    post = get_object_or_404(Post.objects.defer("photo"), pk=post_id)
    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()
    html = render_to_string("garden/comment.html", {"comment": comment_context(request, post, [comment])["comments"][0]}, request=request)
    return JsonResponse({"html": html, "comment_count": post.comments.count()}, status=201)


@require_POST
@ajax_login_required("Please log in to delete this comment.")
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=comment_id)
    if not can_delete(request.user, comment.author):
        return JsonResponse({"message": "You can only delete your own comments."}, status=403)
    post = comment.post
    comment.delete()
    return JsonResponse({"comment_count": post.comments.count()})


@require_POST
@ajax_moderator_required("Only moderators can change the plant of the week.")
def set_plant_of_the_week(request):
    form = PlantOfTheWeekForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    form.save()
    html = render_to_string("garden/plant_of_the_week.html", plant_of_the_week_context(request.user), request=request)
    return JsonResponse({"html": html})
