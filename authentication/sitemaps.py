from django.utils import timezone
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Movie, TMDBMovie

class StaticSitemap(Sitemap):
    priority = 0.7  # Slightly higher for homepage
    changefreq = 'daily'

    def items(self):
        return ['home_view', 'all_movies', 'manual_movies']  # Include key static pages

    def location(self, item):
        return reverse(f'auth:{item}')
    
    def lastmod(self, item):
        return timezone.now()

class TMDBMovieSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9  # Higher for content pages

    def items(self):
        return TMDBMovie.objects.filter(is_indexable=True).order_by('tmdb_id')  # Add ordering

    def location(self, obj):
        return reverse('auth:movie_detail', args=[obj.slug])
        
        # return reverse('auth:movie_detail', args=[obj.tmdb_id])

    def lastmod(self, obj):
        return obj.last_content_update or obj.last_updated
        # return getattr(obj, 'last_updated', None)  # Add last_updated field if needed

class ManualMovieSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Movie.objects.filter(manually_added=True, is_indexable=True).order_by('id')  # Add ordering
    def location(self, obj):
        return reverse('auth:movie_detail1', args=[obj.slug])
        # return reverse('auth:movie_detail1', args=[obj.id])

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at  # Fallback to created_at if no updates