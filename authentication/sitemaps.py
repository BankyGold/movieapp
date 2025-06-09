from django.utils import timezone
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Movie, TMDBMovie

class StaticSitemap(Sitemap):
    priority = 0.7
    changefreq = 'daily'

    def items(self):
        return ['home_view', 'all_movies', 'manual_movies']

    def location(self, item):
        return reverse(f'auth:{item}')

    def lastmod(self, item):
        return timezone.now()

class TMDBMovieSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return TMDBMovie.objects.filter(is_indexable=True).order_by('tmdb_id')

    def location(self, obj):
        from django.http import HttpRequest
        request = HttpRequest()
        request.META['SERVER_NAME'] = 'yourdomain.com'  # Replace with your domain
        request.META['SERVER_PORT'] = '443'
        request.META['wsgi.url_scheme'] = 'https'
        return request.build_absolute_uri(reverse('auth:movie_detail', args=[obj.slug]))

    def lastmod(self, obj):
        return obj.last_content_update or obj.last_updated

class ManualMovieSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Movie.objects.filter(manually_added=True, is_indexable=True).order_by('id')

    def location(self, obj):
        from django.http import HttpRequest
        request = HttpRequest()
        request.META['SERVER_NAME'] = 'moviezcine.com'  # Replace with your domain
        request.META['SERVER_PORT'] = '443'
        request.META['wsgi.url_scheme'] = 'https'
        return request.build_absolute_uri(reverse('auth:movie_detail1', args=[obj.slug]))

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at