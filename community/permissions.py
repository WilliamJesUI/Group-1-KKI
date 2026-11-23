from rest_framework.permissions import BasePermission, SAFE_METHODS
from growyourgarden.permissions import can_delete, is_moderator

class IsAuthorOrReadOnly(BasePermission):
    message = "Only the author can change this."

    def has_permission(self, request, view):
        # Anyone can read; writing requires login
        return request.method in SAFE_METHODS or request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return can_delete(request.user, obj.author)   # author or moderator
        return obj.author_id == request.user.id           # edit: author only