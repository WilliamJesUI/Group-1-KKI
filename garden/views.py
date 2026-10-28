from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Post, PlantOfTheWeek, Comment
from .forms import PostForm, CommentForm
from events.models import Event


def show_garden(request):
    posts = Post.objects.all().prefetch_related('likes', 'author', 'comments__author')
    
    selected_category = request.GET.get('category', '')
    if selected_category:
        posts = posts.filter(category=selected_category)
    
    upcoming_events = Event.objects.filter(start_time__gte=timezone.now()).order_by('start_time')[:3]
    plant_of_week = PlantOfTheWeek.objects.first()
    
    for post in posts:
        post.is_liked = request.user.is_authenticated and request.user in post.likes.all()
        post.is_author = request.user == post.author
        post.can_edit = request.user.is_authenticated and (request.user == post.author or request.user.is_staff)
        post.comment_form = CommentForm()

    context = {
        'posts': posts,
        'upcoming_events': upcoming_events,
        'form': PostForm(),
        'selected_category': selected_category,
        'plant_of_week': plant_of_week,
    }
    return render(request, 'garden/garden.html', context)


@login_required
@require_POST
def create_post_ajax(request):
    form = PostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return JsonResponse({'status': 'success', 'post_id': str(post.id)}, status=201)
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@login_required
@require_POST
def edit_post_ajax(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not (request.user == post.author or request.user.is_staff):
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
    
    form = PostForm(request.POST, instance=post)
    if form.is_valid():
        form.save()
        return JsonResponse({'status': 'success'}, status=200)
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_post_ajax(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not (request.user == post.author or request.user.is_staff):
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
    
    post.delete()
    return JsonResponse({'status': 'success'}, status=200)


@login_required
@require_POST
def toggle_like_ajax(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'status': 'success', 
        'liked': liked, 
        'like_count': post.likes.count()
    })


@login_required
@require_POST
def add_comment_ajax(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return JsonResponse({
            'status': 'success', 
            'comment': {
                'author': comment.author.first_name or comment.author.username,
                'initial': (comment.author.first_name or comment.author.username)[0].upper(),
                'text': comment.text
            }
        }, status=201)
    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)