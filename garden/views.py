from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Post, Comment, PlantOfTheWeek
from .forms import PostForm, CommentForm
from events.models import Event

def json_form_errors(form):
    return {field: [error["message"] for error in errors] for field, errors in form.errors.get_json_data().items()}

def garden_list(request):
    posts = list(Post.objects.select_related("author").prefetch_related("likes", "comments__author"))
    selected_category = request.GET.get("category", "").strip()
    selected_plant = request.GET.get("plant", "").strip()
    query = request.GET.get("q", "").strip()
    
    valid_categories = dict(Post.PLANT_CATEGORIES)
    if selected_category not in valid_categories:
        selected_category = ""
        
    filtered_posts = []
    for post in posts:
        post.is_liked = request.user.is_authenticated and post.likes.filter(pk=request.user.pk).exists()
        post.can_manage = request.user.is_authenticated and (request.user.is_staff or post.author_id == request.user.pk)
        
        if selected_category and selected_category not in post.display_categories:
            continue
        if selected_plant and selected_plant.casefold() != (post.plant_tag or "").casefold():
            continue
        if query:
            searchable = " ".join([post.caption or "", post.plant_tag or "", post.category or "", " ".join(post.display_categories)])
            if query.casefold() not in searchable.casefold():
                continue
        filtered_posts.append(post)

    context = {
        "posts": filtered_posts,
        "upcoming_events": Event.objects.filter(start_time__gte=timezone.now()).order_by("start_time")[:3],
        "plant_of_week": PlantOfTheWeek.objects.first(),
        "form": PostForm(),
        "comment_form": CommentForm(),
        "selected_category": selected_category,
        "selected_plant": selected_plant,
        "plant_options": Post.objects.exclude(plant_tag="").order_by("plant_tag").values_list("plant_tag", flat=True).distinct(),
        "plant_categories": Post.PLANT_CATEGORIES,
        "query": query,
    }
    return render(request, "garden/garden.html", context)

def login_required_json(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Please log in."}, status=403)
    return None

def can_manage_post(user, post):
    return user.is_authenticated and (user.is_staff or post.author_id == user.pk)

def can_manage_comment(user, comment):
    return user.is_authenticated and (user.is_staff or comment.author_id == user.pk)

@require_POST
def create_post_ajax(request):
    error = login_required_json(request)
    if error: return error
    form = PostForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"status": "error", "errors": json_form_errors(form)}, status=400)
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return JsonResponse({
        "status": "success", "post_id": str(post.pk), "caption": post.caption,
        "image_url": post.image_url, "plant_tag": post.plant_tag, "categories": post.categories
    }, status=201)

@require_POST
def toggle_like_ajax(request, post_id):
    error = login_required_json(request)
    if error: return error
    post = get_object_or_404(Post, pk=post_id)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    return JsonResponse({"status": "success", "liked": liked, "like_count": post.likes.count()})

@require_POST
def edit_post_ajax(request, post_id):
    error = login_required_json(request)
    if error: return error
    post = get_object_or_404(Post, pk=post_id)
    if not can_manage_post(request.user, post):
        return JsonResponse({"status": "error", "message": "You cannot edit."}, status=403)
    form = PostForm(request.POST, instance=post)
    if not form.is_valid():
        return JsonResponse({"status": "error", "errors": json_form_errors(form)}, status=400)
    form.save()
    return JsonResponse({
        "status": "success", "caption": post.caption, "image_url": post.image_url, 
        "plant_tag": post.plant_tag, "categories": post.categories
    })

@require_POST
def delete_post_ajax(request, post_id):
    error = login_required_json(request)
    if error: return error
    post = get_object_or_404(Post, pk=post_id)
    if not can_manage_post(request.user, post):
        return JsonResponse({"status": "error", "message": "You cannot delete."}, status=403)
    post.delete()
    return JsonResponse({"status": "success"})

@require_POST
def add_comment_ajax(request, post_id):
    error = login_required_json(request)
    if error: return error
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"status": "error", "errors": json_form_errors(form)}, status=400)
    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()
    return JsonResponse({"status": "success", "comment_id": comment.pk, "author": request.user.username, "text": comment.text}, status=201)