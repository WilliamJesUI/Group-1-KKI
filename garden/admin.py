from django.contrib import admin
from .models import Post, Comment, PlantOfTheWeek

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(PlantOfTheWeek)