"""
Shared login and moderator checks for AJAX views. Any module can use them.

A moderator is a user with "Staff status" ticked in /admin/ (user.is_staff).
Moderators can delete anyone's posts and comments to keep the site clean,
but they can't edit other people's words.

Use them like this:

    from growyourgarden.permissions import ajax_login_required, can_delete

    @require_POST
    @ajax_login_required("Please log in to like posts.")
    def toggle_like(request, post_id):
        ...
        if not can_delete(request.user, post.author):
            return JsonResponse({"message": "You can only delete your own posts."}, status=403)

More info: docs/TEAM-GUIDE.md
"""
from functools import wraps

from django.http import JsonResponse


def is_moderator(user):
    return user.is_authenticated and user.is_staff


def can_delete(user, author):
    """The author can delete their own things, and moderators can delete anything."""
    return user.is_authenticated and (user == author or user.is_staff)


def ajax_login_required(message="Please log in first."):
    """Like Django's @login_required, but for fetch() requests: a JSON 403 with a message
    instead of a redirect to the login page, so the page can show the message as a toast."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"message": message}, status=403)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def ajax_moderator_required(message="Only moderators can do this."):
    """For admin-only actions like picking the plant of the week. JSON 403 for everyone else."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not is_moderator(request.user):
                return JsonResponse({"message": message}, status=403)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
