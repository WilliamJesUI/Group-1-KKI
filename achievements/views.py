from django.shortcuts import render

# Sample data that matches the Figma design. Later this will come from the database.
STATS = [
    {"icon": "img/icons/ach-award.svg", "value": 8, "label": "Badges unlocked"},
    {"icon": "img/icons/ach-sprout.svg", "value": 4, "label": "Day garden streak"},
    {"icon": "img/icons/ach-leaf.svg", "value": 6, "label": "Plants thriving"},
    {"icon": "img/icons/ach-users.svg", "value": 12, "label": "Posts shared"},
]

MILESTONES = [
    {"title": "First Sprout", "description": "Add your first plant", "percent": 100,
     "icon": "img/icons/ach-sprout-lg.svg", "tone": "bg-brand-soft"},
    {"title": "First Harvest", "description": "Log your first harvest", "percent": 70,
     "icon": "img/icons/ach-award-lg.svg", "tone": "bg-pink"},
    {"title": "7 Day Streak", "description": "Check in for seven days", "percent": 57,
     "icon": "img/icons/ach-calendar-lg.svg", "tone": "bg-lilac"},
    {"title": "Good Neighbor", "description": "Answer 10 questions", "percent": 40,
     "icon": "img/icons/ach-users-lg.svg", "tone": "bg-[#b8fff8]"},
]


def show_achievements(request):
    unlocked, total = 8, 12
    context = {
        "unlocked": unlocked,
        "total": total,
        "remaining": total - unlocked,
        "progress_percent": round(unlocked / total * 100),
        "milestones_in_progress": 4,
        "stats": STATS,
        "milestones": MILESTONES,
    }
    return render(request, "achievements.html", context)