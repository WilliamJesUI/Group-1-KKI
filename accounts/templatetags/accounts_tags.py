from django import template

from accounts.models import AVATAR_BG_CLASSES, initials_for

register = template.Library()

# Size classes for {% avatar user "sm" %}, "md" (the default) or "lg"
AVATAR_SIZES = {
    "sm": "size-8 text-[11px]",
    "md": "size-10 text-sm",
    "lg": "size-16 text-xl",
}


def get_profile(user):
    # user.profile raises an error that is also an AttributeError when the user has no Profile, so getattr() gives None
    return getattr(user, "profile", None)


@register.filter
def avatar_bg_class(user):
    """The background class of a user's initials avatar, e.g. bg-lilac. Use it as: {{ post.author|avatar_bg_class }}"""
    profile = get_profile(user)
    return profile.avatar_bg_class if profile else AVATAR_BG_CLASSES["green"]


@register.filter
def avatar_initials(user):
    """The avatar letters. Use it as: {{ post.author|avatar_initials }}"""
    profile = get_profile(user)
    return profile.initials if profile else initials_for(user.first_name or user.username)


@register.inclusion_tag("accounts/_avatar.html")
def avatar(user, size="md"):
    """
    The round avatar of a user: their profile picture, or their two initials on their own color.
    Use it as: {% load accounts_tags %} {% avatar post.author %} or {% avatar post.author "lg" %}
    """
    profile = get_profile(user)
    return {
        "picture": profile.profile_picture if profile else "",
        "bg_class": avatar_bg_class(user),
        "initials": avatar_initials(user),
        "size_class": AVATAR_SIZES.get(size, AVATAR_SIZES["md"]),
    }
