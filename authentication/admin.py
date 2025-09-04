from django.contrib import admin
from .models import User, Comment, Movie, MovieView, Commentmovie, Genre, TMDBMovie
from django.utils import timezone
from datetime import datetime, timedelta

# Register your models here.

admin.site.register(User)
admin.site.register(Comment)

class MovieAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'release_year', 
        'country', 
        'display_genres',  # Use the method instead of 'genre'
        'running_time', 
        'manually_added', 
        'unique_views_this_month', 
        'manual_adds_this_month', 
        'comments_this_month'
    )
    list_filter = ('country', 'release_year', 'manually_added', 'genre')  # Filtering by genre is fine
    search_fields = ('title', 'description')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'release_year', 'poster_image', 'poster_image_url',
        'slug', 'running_time', 'is_indexable', 'country', 'genre',
        'trailer_link', 'movie_link', 'pg_rated', 'rated', 'manually_added',
        'meta_keywords', 'meta_description' )
        }),
    )
    filter_horizontal = ('genre',)  # Re-enable for user-friendly multi-select

    def display_genres(self, obj):
        """Display genres as a comma-separated list in the admin."""
        return ", ".join(genre.name for genre in obj.genre.all())
    display_genres.short_description = "Genres"

    def unique_views_this_month(self, obj):
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return MovieView.objects.filter(movie=obj, viewed_at__gte=start_of_month).values('user').distinct().count()
    unique_views_this_month.short_description = "Unique Views This Month"

    def manual_adds_this_month(self, obj):
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return Movie.objects.filter(manually_added=True, created_at__gte=start_of_month).count()
    manual_adds_this_month.short_description = "Manual Adds This Month"

    def comments_this_month(self, obj):
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return obj.comments.filter(created_at__gte=start_of_month).count()
    comments_this_month.short_description = "Comments This Month"

admin.site.register(Movie, MovieAdmin)
admin.site.register(MovieView)
admin.site.register(Commentmovie)  # Check if this should be 'Comment' instead
admin.site.register(Genre)

@admin.register(TMDBMovie)
class TMDBMovieAdmin(admin.ModelAdmin):
    search_fields = ['title', 'tmdb_id']
    list_display = ("title", "tmdb_id", "is_indexable", "last_updated")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_indexable=False)  
