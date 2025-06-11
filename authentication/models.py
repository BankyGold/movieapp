import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.text import slugify

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email is required'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)  # Ensure password is hashed properly
        else:
            raise ValueError('Password is required')
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)
    
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    first_name = models.CharField(max_length=12)
    last_name = models.CharField(max_length=12)
    date_joined = models.DateTimeField(auto_now_add=True)
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    def save(self, *args, **kwargs):
        if not self.username:
            unique_id = uuid.uuid4().hex[:6]
            self.username = f"{self.first_name.lower()}{self.last_name.lower()}{unique_id}"
        super().save(*args, **kwargs)

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    movie_id = models.IntegerField()  # TMDb movie ID
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_comments', blank=True)
    disliked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='disliked_comments', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} on Movie {self.movie_id}"

class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    GENRE_CHOICES = [
        ('Action', 'Action'),
        ('Adventure', 'Adventure'),
        ('Animation', 'Animation'),
        ('Biography', 'Biography'),
        ('Comedy', 'Comedy'),
        ('Crime', 'Crime'),
        ('Documentary', 'Documentary'),
        ('Drama', 'Drama'),
        ('Family', 'Family'),
        ('Fantasy', 'Fantasy'),
        ('History', 'History'),
        ('Horror', 'Horror'),
        ('Mystery', 'Mystery'),
        ('Romance', 'Romance'),
        ('Science Fiction', 'Science Fiction'),
        ('Thriller', 'Thriller'),
        ('War', 'War'),
        ('Western', 'Western'),
    ]
    name = models.CharField(max_length=50, choices=GENRE_CHOICES, unique=True)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['name']
    
from django.db import models
from django.utils.text import slugify
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import requests
from django.core.files.base import ContentFile

class Movie(models.Model):
    poster_image = models.ImageField(upload_to='posters/', blank=True, null=True)
    poster_image_url = models.URLField(blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    release_year = models.PositiveIntegerField()
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    running_time = models.PositiveIntegerField(help_text="Running time in minutes", blank=True, null=True)
    is_indexable = models.BooleanField(default=True)
    COUNTRY_CHOICES = [
        ('Nigeria', 'Nigeria'),
        ('International', 'International'),
    ]
    country = models.CharField(choices=COUNTRY_CHOICES, max_length=50)
    genre = models.ManyToManyField(Genre, related_name='movies_genre')
    trailer_link = models.URLField(blank=True, null=True)
    movie_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pg_rated = models.CharField(blank=True, null=True, max_length=10)
    rated = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    manually_added = models.BooleanField(default=True)  # Track if added manually
    views = models.ManyToManyField(User, through='MovieView', related_name='viewed_movies')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True, null=True)

    class Meta:
        verbose_name = "Movie"
        verbose_name_plural = "Movies"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.release_year})"
    
    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        if not self.meta_description:
            self.meta_description = f"{self.description[:150]}..." if self.description else f"Watch {self.title} ({self.release_year}) on MovieHub."
        if not self.meta_keywords:
            genres = ', '.join(genre.name for genre in self.genre.all()) if self.genre.exists() else 'movies'
            self.meta_keywords = f"{self.title}, {genres}, {self.country}, MovieHub"
        if self.poster_image:
            img = Image.open(self.poster_image)
            output = BytesIO()
            img = img.convert('RGB')
            img.thumbnail((500, 750))
            img.save(output, format='JPEG', quality=85)
            output.seek(0)
            self.poster_image = InMemoryUploadedFile(
                output, 'ImageField', f"{self.poster_image.name.split('.')[0]}.jpg",
                'image/jpeg', output.tell(), None
            )
        if not self.slug:
            base_slug = slugify(f"{self.title}-{self.release_year}")
            self.slug = base_slug
            if Movie.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                super().save(*args, **kwargs)
                self.slug = f"{base_slug}-{self.pk}"
                kwargs.pop('force_insert', None)
        super().save(*args, **kwargs)

class MovieView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'movie')  # Ensure unique views per user

class Commentmovie(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_manualcomments', blank=True)
    disliked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='disliked_manualcomments', blank=True)

    def __str__(self):
        return f"Comment by {self.user} on {self.movie}"
    class Meta:
        ordering = ['-created_at']

class TMDBMovie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)  # For lastmod in sitemap
    last_content_update = models.DateTimeField(null=True, blank=True)
    is_indexable = models.BooleanField(default=False)  # Changed to False

    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.tmdb_id}")
        if not self.meta_description:
            self.meta_description = f"Explore {self.title} on MovieHub - reviews, trailers, and more."
        if not self.meta_keywords:
            self.meta_keywords = f"{self.title}, movie reviews, TMDB, MovieHub"
        super().save(*args, **kwargs)