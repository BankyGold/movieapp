from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from .models import TMDBMovie, Movie
import requests

@receiver(pre_save, sender=TMDBMovie)
def set_tmdb_movie_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(f"{instance.title}-{instance.tmdb_id}")

@receiver(post_save, sender=Movie)
def ping_google(sender, instance, created, **kwargs):
    if instance.manually_added and instance.is_indexable:
        sitemap_url = '{{ request.scheme }}://{{ request.get_host }}/sitemap.xml'  # Replace with your domain
        requests.get(f'http://www.google.com/ping?sitemap={sitemap_url}')