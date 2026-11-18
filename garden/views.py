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

from growyourgarden.permissions import (
    ajax_login_required,
    ajax_moderator_required,
    can_delete,
    is_moderator
)

from plants.models import Plant


# Available filters displayed above the Garden feed.
GARDEN_FILTERS = [
    ("all", "All plants"),
    ("vegetables", "Vegetables"),
    ("herbs", "Herbs"),
    ("flowers", "Flowers"),
    ("comments", "Most commented"),
    ("mine", "My posts")
]


# Number of comments displayed initially.
COMMENT_PREVIEW_COUNT = 3


def posts_for(user):
    """Returns posts with all information needed by the feed."""

    posts = (
        Post.objects.defer("photo")
        .select_related("author__profile", "plant")
        .annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count("comments", distinct=True)
        )
    )

    if user.is_authenticated:
        # Checks whether the current user has liked each post.
        posts = posts.annotate(
            is_liked=Exists(
                Post.likes.through.objects.filter(
                    post=OuterRef("pk"),
                    user=user
                )
            )
        )

    return posts


def mark_permissions(posts, user):
    """Adds permission flags to every post."""

    for post in posts:

        # Only the author can edit their own post.
        post.can_edit = (
            user.is_authenticated
            and post.author_id == user.pk
        )

        # Authors and moderators can delete posts.
        post.can_delete = can_delete(user, post.author)

    return posts


def filter_posts(posts, selected_filter, user):
    """Filters posts based on the selected category."""

    if selected_filter == "mine":
        return (
            posts.filter(author=user)
            if user.is_authenticated
            else posts.none()
        )

    if selected_filter == "comments":
        return posts.order_by('-comment_count', '-created_at')
    
    if selected_filter in ("vegetables", "herbs", "flowers"):
        return posts.filter(
            plant__category=selected_filter
        )

    return posts


def get_plant_of_the_week():
    """Returns the latest moderator selection or an automatic weekly plant."""

    pick = PlantOfTheWeek.objects.select_related("plant").first()

    if pick:
        return pick.plant, pick.short_line

    # If no moderator selection exists, use plants with images.
    plants = Plant.objects.exclude(
        image_url=""
    ).order_by("pk")

    count = plants.count()

    if not count:
        return None, ""

    # The selected plant changes according to the week number.
    week_number = date.today().isocalendar().week

    return plants[week_number % count], ""


def plant_of_the_week_context(user):
    """Builds the context for the Plant of the Week sidebar."""

    plant, short_line = get_plant_of_the_week()

    context = {
        "week_plant": plant,
        "week_short_line": short_line
    }

    if is_moderator(user):
        # Only moderators receive the editing form.
        context["week_form"] = PlantOfTheWeekForm(
            initial={
                "plant": plant,
                "short_line": short_line
            }
        )

    return context


def render_card(request, post):
    """Renders one post card as HTML for AJAX responses."""

    post = mark_permissions(
        [posts_for(request.user).get(pk=post.pk)],
        request.user
    )[0]

    return render_to_string(
        "garden/post_card.html",
        {
            "post": post,
            "user": request.user
        },
        request=request
    )


# Makes sure the browser receives a CSRF cookie for AJAX requests.
@ensure_csrf_cookie
def show_garden(request):
    """Displays the main Garden page."""

    # Read the selected filter from the URL.
    selected_filter = request.GET.get("filter", "all")

    # Use the default filter if the requested value is invalid.
    if selected_filter not in dict(GARDEN_FILTERS):
        selected_filter = "all"

    posts = filter_posts(
        posts_for(request.user),
        selected_filter,
        request.user
    )

    # Optional plant-specific filtering.
    plant_slug = request.GET.get("plant", "").strip()

    selected_plant = (
        Plant.objects.filter(slug=plant_slug).first()
        if plant_slug
        else None
    )

    if selected_plant:
        posts = posts.filter(plant=selected_plant)

    posts = mark_permissions(
        list(posts),
        request.user
    )

    context = {
        "posts": posts,
        "selected_filter": selected_filter,
        "selected_plant": selected_plant
    }

    # AJAX filter requests receive only the feed HTML.
    if request.GET.get("partial") == "1":
        return render(
            request,
            "garden/post_feed.html",
            context
        )

    # Additional information needed by the full page.
    context.update({
        "garden_filters": GARDEN_FILTERS,

        "upcoming_events": Event.objects.defer(
            "cover_image"
        ).filter(
            start_time__gte=timezone.now()
        ).order_by("start_time")[:3],

        "form": PostForm(),
        "comment_form": CommentForm(),

        **plant_of_the_week_context(request.user),
    })

    return render(
        request,
        "garden/garden.html",
        context
    )


def show_post_photo(request, post_id):
    """Returns an uploaded post photo from the database."""

    post = get_object_or_404(
        Post,
        pk=post_id
    )

    if not post.photo_type:
        raise Http404("This post has no uploaded photo.")

    response = HttpResponse(
        bytes(post.photo),
        content_type=post.photo_type
    )

    # Allows the browser to cache the image for one day.
    response["Cache-Control"] = "public, max-age=86400"

    return response


def save_post_from_form(post, form):
    """Handles photo upload and photo removal for create and edit."""

    photo = form.cleaned_data["photo_upload"]

    if photo:
        # Save the uploaded image bytes and MIME type.
        post.photo = photo["data"]
        post.photo_type = photo["type"]
        post.image_url = ""

    elif form.cleaned_data["remove_photo"]:
        # Remove all existing photo information.
        post.photo = None
        post.photo_type = ""
        post.image_url = ""

    post.save()


@require_POST
@ajax_login_required("Please log in to share a post.")
def create_post(request):
    """Creates a new Garden post."""

    form = PostForm(
        request.POST,
        request.FILES
    )

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400
        )

    post = form.save(commit=False)

    # The author comes from the authenticated session.
    post.author = request.user

    save_post_from_form(post, form)

    return JsonResponse(
        {"html": render_card(request, post)},
        status=201
    )


@require_POST
@ajax_login_required("Please log in to edit this post.")
def edit_post(request, post_id):
    """Updates an existing post."""

    post = get_object_or_404(
        Post,
        pk=post_id
    )

    # Only the original author can edit the post.
    if post.author != request.user:
        return JsonResponse(
            {"message": "You can only edit your own posts."},
            status=403
        )

    form = PostForm(
        request.POST,
        request.FILES,
        instance=post
    )

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400
        )

    save_post_from_form(
        form.save(commit=False),
        form
    )

    return JsonResponse(
        {"html": render_card(request, post)}
    )


@require_POST
@ajax_login_required("Please log in to delete this post.")
def delete_post(request, post_id):
    """Deletes a post if the user has permission."""

    post = get_object_or_404(
        Post,
        pk=post_id
    )

    if not can_delete(request.user, post.author):
        return JsonResponse(
            {"message": "You can only delete your own posts."},
            status=403
        )

    post.delete()

    return JsonResponse({
        "deleted": True
    })


@require_POST
@ajax_login_required("Please log in to like posts.")
def like_post(request, post_id):
    """Adds or removes the current user's like."""

    post = get_object_or_404(
        Post.objects.defer("photo"),
        pk=post_id
    )

    # Explicitly set the like state instead of simply toggling it.
    if request.POST.get("liked") == "true":
        post.likes.add(request.user)
    else:
        post.likes.remove(request.user)

    return JsonResponse({
        "liked": post.likes.filter(
            pk=request.user.pk
        ).exists(),

        "like_count": post.likes.count()
    })


def comment_context(request, post, comments):
    """Adds deletion permissions to each comment."""

    for comment in comments:
        comment.can_delete = can_delete(
            request.user,
            comment.author
        )

    return {
        "post": post,
        "comments": comments,
        "user": request.user
    }


@require_GET
def show_comments(request, post_id):
    """Loads comments for a specific post."""

    post = get_object_or_404(
        Post.objects.defer("photo"),
        pk=post_id
    )

    comments = post.comments.select_related(
        "author__profile"
    )

    total = comments.count()

    # Initially display only the newest three comments.
    if (
        request.GET.get("all") != "1"
        and total > COMMENT_PREVIEW_COUNT
    ):

        comments = list(
            comments.order_by("-created_at")[
                :COMMENT_PREVIEW_COUNT
            ]
        )[::-1]

        hidden_count = total - COMMENT_PREVIEW_COUNT

    else:
        comments = list(comments)
        hidden_count = 0

    context = comment_context(
        request,
        post,
        comments
    )

    context["hidden_count"] = hidden_count

    return render(
        request,
        "garden/comment_list.html",
        context
    )


@require_POST
@ajax_login_required("Please log in to comment.")
def add_comment(request, post_id):
    """Creates a new comment."""

    post = get_object_or_404(
        Post.objects.defer("photo"),
        pk=post_id
    )

    form = CommentForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400
        )

    comment = form.save(commit=False)

    # Assign the post and author on the server.
    comment.post = post
    comment.author = request.user

    comment.save()

    html = render_to_string(
        "garden/comment.html",
        {
            "comment": comment_context(
                request,
                post,
                [comment]
            )["comments"][0]
        },
        request=request
    )

    return JsonResponse(
        {
            "html": html,
            "comment_count": post.comments.count()
        },
        status=201
    )


@require_POST
@ajax_login_required("Please log in to delete this comment.")
def delete_comment(request, comment_id):
    """Deletes a comment if the user has permission."""

    comment = get_object_or_404(
        Comment.objects.select_related("post"),
        pk=comment_id
    )

    if not can_delete(request.user, comment.author):
        return JsonResponse(
            {"message": "You can only delete your own comments."},
            status=403
        )

    post = comment.post

    comment.delete()

    return JsonResponse({
        "comment_count": post.comments.count()
    })


@require_POST
@ajax_moderator_required(
    "Only moderators can change the plant of the week."
)
def set_plant_of_the_week(request):
    """Allows moderators to select the Plant of the Week."""

    form = PlantOfTheWeekForm(request.POST)

    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400
        )

    form.save()

    html = render_to_string(
        "garden/plant_of_the_week.html",
        plant_of_the_week_context(request.user),
        request=request
    )

    return JsonResponse({
        "html": html
    })