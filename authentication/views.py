from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomLoginForm, CustomRegistrationForm
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.cache import cache_page
from .models import Comment, Movie, MovieView, Commentmovie, TMDBMovie
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.templatetags.static import static
from django.utils.text import slugify
from datetime import datetime
import requests
import random
import logging

    
# Create your views here.
def login_view(request):
    errors = None
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('auth:home_view')  # Change to your home page or dashboard
        else:
            errors = form.errors  # Store form errors
            
    else:
        form = CustomLoginForm()
    return render(request, 'account/login.html', {'form': form, 'errors': errors})

def signup_view(request):
    errors = None
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('auth:home_view')
            print(email)
        else:
            errors = form.errors  # Capture form errors
    else:
        form = CustomRegistrationForm()
    return render(request, 'account/signup.html', {'form': form, 'errors': errors})

@cache_page(60 * 15)
def index_view(request):
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    genre_map = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
                 99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
                 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
                 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"}
    genre_name_to_id = {v: k for k, v in genre_map.items()}
    popular_url = f'https://api.themoviedb.org/3/movie/popular?api_key={api_key}'
    upcoming_url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={api_key}'
    trending_url = f'https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}'
    scorebat_url = f'https://www.scorebat.com/video-api/v3/feed/?token={settings.SCOREBAT_ACCESS_TOKEN}'  # Add Scorebat URL
    movies = []
    query = request.GET.get('q', '').strip()
    
    if query:
        search_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}'
        try:
            search_response = requests.get(search_url)
            search_response.raise_for_status()
            tmdb_movies = search_response.json().get('results', [])
            for movie in tmdb_movies:
                movie_obj, _ = TMDBMovie.objects.get_or_create(
                    tmdb_id=movie['id'],
                    defaults={'title': movie['title'], 'slug': slugify(f"{movie['title']}-{movie['id']}")}
                )
                movies.append({
                    'id': movie['id'], 'title': movie['title'], 'poster_path': movie['poster_path'],
                    'vote_average': movie['vote_average'], 'release_date': movie['release_date'],
                    'genre_ids': movie['genre_ids'], 'source': 'tmdb', 'slug': movie_obj.slug
                })
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
        manual_movies = Movie.objects.filter(title__icontains=query, manually_added=True).order_by('-created_at')
        for movie in manual_movies:
            genre_ids = [genre_name_to_id.get(genre.name, 0) for genre in movie.genre.all()]
            movies.append({
                'id': movie.id, 'title': movie.title, 'poster_path': movie.poster_image.url if movie.poster_image else None,
                'vote_average': movie.views.count(), 'release_date': str(movie.release_year) + "-01-01" if movie.release_year else None,
                'genre_ids': genre_ids, 'source': 'manual', 'slug': movie.slug
            })
        
        # Search Scorebat football videos
        try:
            scorebat_response = requests.get(scorebat_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            scorebat_response.raise_for_status()
            scorebat_videos = scorebat_response.json().get('response', [])
            for video in scorebat_videos:
                if not isinstance(video, dict) or 'title' not in video:
                    continue
                # Filter by query (case-insensitive match on title)
                if query.lower() in video['title'].lower():
                    video_date = datetime.strptime(video['date'], '%Y-%m-%dT%H:%M:%S%z')
                    video_id = video['videos'][0]['id'] if video.get('videos') and isinstance(video['videos'], list) and len(video['videos']) > 0 else ''
                    competition_name = video['competition'] if isinstance(video['competition'], str) else video['competition'].get('name', 'Unknown Competition')
                    movies.append({
                        'id': video_id, 'title': video['title'], 'poster_path': video.get('thumbnail', None),
                        'vote_average': None, 'release_date': video_date.strftime('%Y-%m-%d'),
                        'genre_ids': [0],  # Dummy genre ID; could map "Football" to a custom ID
                        'source': 'football', 'slug': video_id  # Use video_id as slug for football videos
                    })
        except requests.RequestException as e:
            print(f"Scorebat API error: {e}")
        movies.sort(key=lambda x: x['title'].lower())
    
    popular = requests.get(popular_url).json().get('results', [])
    random.shuffle(popular)  # Shuffle the full list
    popular = popular[:10]   # Take the first 10 after shuffling

    # Fetch and randomize upcoming movies
    upcoming = requests.get(upcoming_url).json().get('results', [])
    random.shuffle(upcoming)  # Shuffle the full list
    upcoming = upcoming[:5]   # Take the first 5 after shuffling

    # Fetch and randomize trending movies
    trending = requests.get(trending_url).json().get('results', [])
    random.shuffle(trending)  # Shuffle the full list
    trending = trending[:12]  # Take the first 12 after shuffling

    for movie in popular + upcoming + trending:
        movie_obj, _ = TMDBMovie.objects.get_or_create(
            tmdb_id=movie['id'],
            defaults={'title': movie['title'], 'slug': slugify(f"{movie['title']}-{movie['id']}")}
        )
        movie['slug'] = movie_obj.slug  # Add slug to API data
    
    seo_title = f"Search '{query[:20]}...' - MovieHub Movies" if query else "MovieHub - Latest 2025 Movies & Reviews"
    seo_description = (
        f"Search '{query}' movies on MovieHub. Find trailers, reviews, and more." if query
        else "Discover the latest 2025 movies, popular releases, trending films, and reviews on MovieHub."
    )
    seo_robots = 'noindex, nofollow' if query else 'index, follow'
    movie_list_schema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "Movie", "name": movie['title'], "url": request.build_absolute_uri(reverse('auth:movie_detail', args=[movie['slug']]))}
            for movie in trending[:5]
        ]
    } if not query else None
    return render(request, 'account/index.html', {
        'popular': popular, 'movies': movies, 'query': query, 'upcoming': upcoming, 'trending': trending,
        'genre_map': genre_map, 'seo_title': seo_title, 'seo_description': seo_description,
        'canonical_url': request.build_absolute_uri(request.path + ('?q=' + query if query else '')),
        'seo_robots': seo_robots, 'movie_list_schema': movie_list_schema
    })

def popular_movies(request):
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    popular_url = f'https://api.themoviedb.org/3/movie/popular?api_key={api_key}'
    movies = requests.get(popular_url).json().get('results', [])[:10]
    for movie in movies:
        TMDBMovie.objects.get_or_create(tmdb_id=movie['id'], defaults={'title': movie['title']})
    seo_title = "Popular Movies - MovieHub"
    seo_description = "Discover the most popular movies right now on MovieHub."
    return render(request, 'account/popular.html', {
        'movies': movies, 'seo_title': seo_title, 'seo_description': seo_description,
        'canonical_url': request.build_absolute_uri()
    })

def upcoming_movies(request):
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    upcoming_url = f'https://api.themoviedb.org/3/movie/upcoming?api_key={api_key}'
    movies = requests.get(upcoming_url).json().get('results', [])[:10]
    for movie in movies:
        TMDBMovie.objects.get_or_create(tmdb_id=movie['id'], defaults={'title': movie['title']})
    seo_title = "Upcoming Movies - MovieHub"
    seo_description = "Check out upcoming movie releases on MovieHub."
    return render(request, 'account/upcoming.html', {
        'movies': movies, 'seo_title': seo_title, 'seo_description': seo_description,
        'canonical_url': request.build_absolute_uri()
    })
logger = logging.getLogger(__name__)

# Conditional caching: only apply in production
def movie_detail(request, slug):
    # Get the TMDBMovie object by slug
    movie_obj = get_object_or_404(TMDBMovie, slug=slug)
    movie_id = movie_obj.tmdb_id
    # Apply caching based on movie_id
    cache_decorator = cache_page(60 * 15, key_prefix=f"movie_detail_{movie_id}") if not settings.DEBUG else lambda x: x
    view = cache_decorator(movie_detail_inner)(request, movie_id, slug=slug)  # Pass slug to inner function
    return view


def movie_detail_inner(request, movie_id, slug):
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    movie_url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}'
    credits_url = f'https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={api_key}'
    videos_url = f'https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={api_key}'
    release_dates_url = f'https://api.themoviedb.org/3/movie/{movie_id}/release_dates?api_key={api_key}'
    reviews_url = f'https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={api_key}'

    # Fetch movie data with error handling
    try:
        movie_response = requests.get(movie_url)
        movie_response.raise_for_status()
        movie = movie_response.json()
    except requests.RequestException:
        return render(request, 'account/error.html', {'message': 'Movie not found'}, status=404)

    credits = requests.get(credits_url).json()
    videos = requests.get(videos_url).json().get('results', [])
    reviews = requests.get(reviews_url).json().get('results', [])[:5]
    release_dates = requests.get(release_dates_url).json().get('results', [])
    director = next((m for m in credits.get('crew', []) if m['job'] == 'Director'), None)
    certification = next((r["certification"] for item in release_dates if item["iso_3166_1"] == "US" for r in item.get("release_dates", []) if r.get("certification")), None)
    trailer = next((v for v in videos if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)

    # Comments and pagination
    comments = Comment.objects.filter(movie_id=movie_id)
    paginator = Paginator(comments, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Handle comment submission
    if request.method == 'POST' and 'content' in request.POST and request.user.is_authenticated:
        content = request.POST.get('content').strip()
        if content:
            Comment.objects.create(user=request.user, movie_id=movie_id, content=content)
            cache.delete(f"movie_detail_{movie_id}")
            return redirect('auth:movie_detail', slug=slug)

    # Sitemap integration
    movie_obj, created = TMDBMovie.objects.get_or_create(
        tmdb_id=movie_id, 
        defaults={'title': movie['title'], 'slug': slugify(f"{movie['title']}-{movie_id}")}
    )
    if not movie_obj.slug:  # Ensure slug is always set
        movie_obj.slug = slugify(f"{movie['title']}-{movie_id}")
        movie_obj.save()

    # SEO metadata
    seo_title = f"{movie['title'][:40]} ({movie['release_date'][:4]}) - MovieHub"
    seo_description = f"{movie['overview'][:120]}... Watch {movie['title']} reviews, trailers on MovieHub."
    seo_keywords = f"{movie['title']}, {', '.join(g['name'] for g in movie.get('genres', []))}, movie reviews, MovieHub"
    seo_robots = 'index, follow'

    # Structured data for Movie
    movie_schema = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "name": movie['title'],
        "url": request.build_absolute_uri(),
        "image": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
        "genre": [g['name'] for g in movie.get('genres', [])],
        "datePublished": movie['release_date'],
        "director": {"@type": "Person", "name": director['name']} if director else None,
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": movie['vote_average'],
            "bestRating": "10",
            "ratingCount": movie['vote_count']
        } if movie.get('vote_average') else None
    }
    
    # Video structured data (if trailer exists)
    if trailer:
        movie_schema["video"] = {
            "@type": "VideoObject",
            "name": f"{movie['title']} Trailer",
            "description": f"Watch the official trailer for {movie['title']}.",
            "thumbnailUrl": f"https://img.youtube.com/vi/{trailer['key']}/0.jpg",
            "contentUrl": f"https://www.youtube.com/watch?v={trailer['key']}",
            "uploadDate": trailer.get('published_at', movie['release_date'])
        }

    return render(request, 'account/details.html', {
        'movie': movie, 'trailer': trailer, 'cast': credits.get('cast', [])[:10], 'certification': certification,
        'director': director, 'reviews': reviews, 'comments': page_obj, 'page_obj': page_obj,
        'seo_title': seo_title, 'seo_description': seo_description, 'seo_keywords': seo_keywords,
        'seo_robots': seo_robots, 'movie_schema': movie_schema, 'canonical_url': request.build_absolute_uri(),
        'prev_page_url': request.build_absolute_uri(f"?page={int(page_number) - 1}") if page_obj.has_previous() else None,
        'next_page_url': request.build_absolute_uri(f"?page={int(page_number) + 1}") if page_obj.has_next() else None,
    })

@login_required
@require_POST
def like_comment(request, comment_id):
    comment = Comment.objects.get(id=comment_id)
    user = request.user
    if user not in comment.liked_by.all():
        comment.liked_by.add(user)
        comment.likes += 1
        if user in comment.disliked_by.all():
            comment.disliked_by.remove(user)
            comment.dislikes -= 1
        comment.save()
        cache_key = f"movie_detail_{comment.movie_id}"
        cache.delete(cache_key)
    return JsonResponse({'likes': comment.likes, 'dislikes': comment.dislikes, 'status': 'success'})

@login_required
@require_POST
def dislike_comment(request, comment_id):
    comment = Comment.objects.get(id=comment_id)
    user = request.user
    if user not in comment.disliked_by.all():
        comment.disliked_by.add(user)
        comment.dislikes += 1
        if user in comment.liked_by.all():
            comment.liked_by.remove(user)
            comment.likes -= 1
        comment.save()
        cache_key = f"movie_detail_{comment.movie_id}"
        cache.delete(cache_key)
    return JsonResponse({'likes': comment.likes, 'dislikes': comment.dislikes, 'status': 'success'})

@cache_page(60 * 15)
def search_movies(request):
    query = request.GET.get('q', '')
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}'
    response = requests.get(url)
    movies = response.json().get('results', [])
    return render(request, 'movies/search.html', {'movies': movies, 'query': query})

def logout(request):
    logout(request)
    return redirect('auth:account_login')

def all_movies(request):
    api_key = '5ebda61e9469961821ac79b7479e5b51'
    page = int(request.GET.get('page', 1))
    genre_url = f'https://api.themoviedb.org/3/genre/movie/list?api_key={api_key}'
    discover_url = f'https://api.themoviedb.org/3/discover/movie?api_key={api_key}&page={page}&sort_by=release_date.desc'

    # Fetch genres with error handling
    try:
        genre_response = requests.get(genre_url)
        genre_response.raise_for_status()
        genres = genre_response.json().get('genres', [])
        genre_map = {g['id']: g['name'] for g in genres}
    except requests.RequestException:
        genre_map = {}

    # Fetch movies with error handling
    try:
        response = requests.get(discover_url)
        response.raise_for_status()
        movies_data = response.json()
        movies = movies_data.get('results', [])  # Get all results (typically 20 per page)
        random.shuffle(movies)  # Shuffle the full list
        movies = movies[:12]  # Take the first 12 after shuffling
        total_pages = movies_data.get('total_pages', 1)
    except requests.RequestException:
        movies = []
        total_pages = 1

    # Add slugs to movies
    

    # Sitemap integration for movie detail pages
    for movie in movies:
        movie_obj, _ = TMDBMovie.objects.get_or_create(
            tmdb_id=movie['id'],
            defaults={'title': movie['title'], 'slug': slugify(f"{movie['title']}-{movie['id']}")}
        )
        movie['slug'] = movie_obj.slug

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.contrib.staticfiles import finders  # To locate static file
        default_image = finders.find('assets/img/postal.jpg')  # Ensure this exists
        default_image_url = '/static/assets/img/postal.jpg' if default_image else 'https://via.placeholder.com/500x750?text=No+Poster'
        
        html = ''  # Start with the row wrapper <div class="row row--grid">
        for movie in movies:
            movie_url = reverse('auth:movie_detail', args=[movie['slug']])
            poster_path = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else default_image_url
            genre_names = [genre_map.get(genre_id, 'Unknown') for genre_id in movie.get('genre_ids', [])[:1]]
            html += (
                f'<div class="col-6 col-sm-4 col-lg-3 col-xl-2">'
                f'    <div class="card">'
                f'        <a href="{movie_url}" class="card__cover">'
                f'            <img src="{poster_path}" alt="{movie["title"]}" onerror="this.src=\'https://via.placeholder.com/500x750?text=No+Poster\'">'
                f'            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M11 1C16.5228 1 21 5.47716 21 11C21 16.5228 16.5228 21 11 21C5.47716 21 1 16.5228 1 11C1 5.47716 5.47716 1 11 1Z" stroke-linecap="round" stroke-linejoin="round"/><path fill-rule="evenodd" clip-rule="evenodd" d="M14.0501 11.4669C13.3211 12.2529 11.3371 13.5829 10.3221 14.0099C10.1601 14.0779 9.74711 14.2219 9.65811 14.2239C9.46911 14.2299 9.28711 14.1239 9.19911 13.9539C9.16511 13.8879 9.06511 13.4569 9.03311 13.2649C8.93811 12.6809 8.88911 11.7739 8.89011 10.8619C8.88911 9.90489 8.94211 8.95489 9.04811 8.37689C9.07611 8.22089 9.15811 7.86189 9.18211 7.80389C9.22711 7.69589 9.30911 7.61089 9.40811 7.55789C9.48411 7.51689 9.57111 7.49489 9.65811 7.49789C9.74711 7.49989 10.1091 7.62689 10.2331 7.67589C11.2111 8.05589 13.2801 9.43389 14.0401 10.2439C14.1081 10.3169 14.2951 10.5129 14.3261 10.5529C14.3971 10.6429 14.4321 10.7519 14.4321 10.8619C14.4321 10.9639 14.4011 11.0679 14.3371 11.1549C14.3041 11.1999 14.1131 11.3999 14.0501 11.4669Z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                f'        </a>'
                f'        <button class="card__add" type="button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M16,2H8A3,3,0,0,0,5,5V21a1,1,0,0,0,.5.87,1,1,0,0,0,1,0L12,18.69l5.5,3.18A1,1,0,0,0,18,22a1,1,0,0,0,.5-.13A1,1,0,0,0,19,21V5A3,3,0,0,0,16,2Zm1,17.27-4.5-2.6a1,1,0,0,0-1,0L7,19.27V5A1,1,0,1,1,8,4h8a1,1,0,1,1,1Z"/></svg></button>'
                f'        <span class="card__rating"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M22,9.67A1,1,0,0,0,21.14,9l-5.69-.83L12.9,3a1,1,0,0,0-1.8,0L8.55,8.16,2.86,9a1,1,0,0,0-.81.68,1,1,0,0,0,.25,1l4.13,4-1,5.68A1,1,0,0,0,6.9,21.44L12,18.77l5.1,2.67a.93.93,0,0,0,.46.12,1,1,0,0,0,.59-.19,1,1,0,0,0,.4-1l-1-5.68,4.13-4A1,1,0,0,0,22,9.67Zm-6.15,4a1,1,0,0,0-.29.88l.72,4.2-3.76-2a1.06,1.06,0,0,0-.94,0l-3.76,2,.72-4.2a1,1,0,0,0-.29-.88l-3-3,4.21-.61a1,1,0,0,0,.76-.55L12,5.7l1.88,3.82a1,1,0,0,0,.76.55l4.21.61Z"/></svg> {movie["vote_average"]}</span>'
                f'        <h3 class="card__title"><a href="{movie_url}">{movie["title"]} {f" ({movie["release_date"][:4]})" if movie.get("release_date") else ""}</a></h3>'
                f'        <ul class="card__list">'
                f'            {"<li>" + genre_names[0] + "</li>" if genre_names else "<li>Unknown</li>"}'
                f'            <li>{movie["release_date"][:4] if movie.get("release_date") else "N/A"}</li>'
                f'        </ul>'
                f'    </div>'
                f'</div>'
            )
        # html += '</div>'  # Close the row wrapper
        return JsonResponse({
            'html': html,
            'has_next': int(page) < total_pages,
            'next_page': int(page) + 1
        })
    
    # SEO metadata (only index page 1)
    seo_title = "All Movies - Latest 2025 Releases | MovieHub" if int(page) == 1 else f"All Movies Page {page} - MovieHub"
    seo_description = (
        "Browse all movies on MovieHub. Latest 2025 releases, classics, and more." if int(page) == 1
        else f"Page {page} of all movies on MovieHub. Explore more releases."
    )
    seo_keywords = "all movies, latest movies 2025, MovieHub" if int(page) == 1 else None
    seo_robots = 'index, follow'

    # Pagination links (for crawling, not indexing)
    prev_page_url = request.build_absolute_uri(f"?page={int(page) - 1}") if int(page) > 1 else None
    next_page_url = request.build_absolute_uri(f"?page={int(page) + 1}") if int(page) < total_pages else None

    # Structured data (only for page 1)
    movie_list_schema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "Movie", "position": idx + 1, "name": movie['title'], "url": request.build_absolute_uri(reverse('auth:movie_detail', args=[movie['slug']]))}
            for idx, movie in enumerate(movies)
        ]
    } if int(page) == 1 else None

    return render(request, 'account/movies.html', {
        'movies': movies, 'page': int(page), 'total_pages': total_pages, 'genre_map': genre_map,
        'seo_title': seo_title, 'seo_description': seo_description, 'seo_keywords': seo_keywords,
        'seo_robots': seo_robots, 'canonical_url': request.build_absolute_uri(),
        'prev_page_url': prev_page_url, 'next_page_url': next_page_url, 'movie_list_schema': movie_list_schema
    })

def manual_movies(request):
    page = request.GET.get('page', 1)
    movies = Movie.objects.filter(manually_added=True).order_by('-created_at')
    per_page = 6
    total_movies = movies.count()
    total_pages = (total_movies + per_page - 1) // per_page
    start = (int(page) - 1) * per_page
    end = start + per_page
    movies_paginated = movies[start:end]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = ''
        for movie in movies_paginated:
            # Use static() to resolve the static URL in Python
            poster_src = movie.poster_image.url if movie.poster_image else static('assets/img/postal.jpg')
            movie_url = reverse('auth:movie_detail1', args=[movie.id])
            html += (
                f'<div class="col-6 col-sm-4 col-lg-3 col-xl-2">'
                f'    <div class="card">'
                f'        <a href="{movie_url}" class="card__cover">'
                f'            <img src="{poster_src}" alt="{movie.title}">'
                f'            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M11 1C16.5228 1 21 5.47716 21 11C21 16.5228 16.5228 21 11 21C5.47716 21 1 16.5228 1 11C1 5.47716 5.47716 1 11 1Z" stroke-linecap="round" stroke-linejoin="round"/><path fill-rule="evenodd" clip-rule="evenodd" d="M14.0501 11.4669C13.3211 12.2529 11.3371 13.5829 10.3221 14.0099C10.1601 14.0779 9.74711 14.2219 9.65811 14.2239C9.46911 14.2299 9.28711 14.1239 9.19911 13.9539C9.16511 13.8879 9.06511 13.4569 9.03311 13.2649C8.93811 12.6809 8.88911 11.7739 8.89011 10.8619C8.88911 9.90489 8.94211 8.95489 9.04811 8.37689C9.07611 8.22089 9.15811 7.86189 9.18211 7.80389C9.22711 7.69589 9.30911 7.61089 9.40811 7.55789C9.48411 7.51689 9.57111 7.49489 9.65811 7.49789C9.74711 7.49989 10.1091 7.62689 10.2331 7.67589C11.2111 8.05589 13.2801 9.43389 14.0401 10.2439C14.1081 10.3169 14.2951 10.5129 14.3261 10.5529C14.3971 10.6429 14.4321 10.7519 14.4321 10.8619C14.4321 10.9639 14.4011 11.0679 14.3371 11.1549C14.3041 11.1999 14.1131 11.3999 14.0501 11.4669Z" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                f'        </a>'
                f'        <button class="card__add" type="button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M16,2H8A3,3,0,0,0,5,5V21a1,1,0,0,0,.5.87,1,1,0,0,0,1,0L12,18.69l5.5,3.18A1,1,0,0,0,18,22a1,1,0,0,0,.5-.13A1,1,0,0,0,19,21V5A3,3,0,0,0,16,2Zm1,17.27-4.5-2.6a1,1,0,0,0-1,0L7,19.27V5A1,1,0,0,1,8,4h8a1,1,0,0,1,1,1Z"/></svg></button>'
                f'        <span class="card__rating"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M22,9.67A1,1,0,0,0,21.14,9l-5.69-.83L12.9,3a1,1,0,0,0-1.8,0L8.55,8.16,2.86,9a1,1,0,0,0-.81.68,1,1,0,0,0,.25,1l4.13,4-1,5.68A1,1,0,0,0,6.9,21.44L12,18.77l5.1,2.67a.93.93,0,0,0,.46.12,1,1,0,0,0,.59-.19,1,1,0,0,0,.4-1l-1-5.68,4.13-4A1,1,0,0,0,22,9.67Zm-6.15,4a1,1,0,0,0-.29.88l.72,4.2-3.76-2a1.06,1,0,0,0-.94,0l-3.76,2,.72-4.2a1,1,0,0,0-.29-.88l-3-3,4.21-.61a1,1,0,0,0,.76-.55L12,5.7l1.88,3.82a1,1,0,0,0,.76.55l4.21.61Z"/></svg> {movie.views.count()}</span>'
                f'        <h3 class="card__title"><a href="{movie_url}">{movie.title} ({movie.release_year})</a></h3>'
                f'        <ul class="card__list">'
                f'            <li>{movie.genre.first if movie.genre.exists() else "No genre"}</li>'
                f'            <li>{movie.release_year}</li>'
                f'        </ul>'
                f'    </div>'
                f'</div>'
            )
        return JsonResponse({
            'html': html,
            'has_next': int(page) < total_pages,
            'next_page': int(page) + 1
        })

    seo_title = f"Local Movies - Page {page} - MovieHub"
    seo_description = f"Explore user-uploaded local movies on MovieHub, page {page}."
    seo_robots = 'index, follow'

    movie_list_schema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "Movie",
                "name": movie.title,
                "description": movie.description[:30] if movie.description else "No description",
                "image": movie.poster_image.url if movie.poster_image else request.build_absolute_uri(static('assets/img/postal.jpg')),
                "datePublished": f"{movie.release_year}-01-01",
                "genre": movie.genre.first().name if movie.genre.exists() else "Unknown"
            }
            for movie in movies_paginated
        ]
    }
    return render(request, 'account/manual.html', {
        'movies': movies_paginated, 'page': int(page), 'total_pages': total_pages,
        'seo_title': seo_title, 'seo_description': seo_description, 'seo_robots': seo_robots,
        'canonical_url': request.build_absolute_uri(), 'movie_list_schema': movie_list_schema
    })


def manual_movie_detail(request, slug):
    # Retrieve movie by slug instead of id
    movie = get_object_or_404(Movie, slug=slug)
    if request.user.is_authenticated:
        MovieView.objects.get_or_create(user=request.user, movie=movie)
    
    if request.method == 'POST' and request.user.is_authenticated:
        content = request.POST.get('content')
        if content:
            Commentmovie.objects.create(movie=movie, user=request.user, content=content)
    
    comments = movie.comments.all().order_by('-created_at')
    paginator = Paginator(comments, 5)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    seo_title = f"{movie.title} ({movie.release_year}) - MovieHub"
    seo_description = f"{movie.description[:150]} - User-uploaded movie on MovieHub."
    seo_robots = 'index, follow'
    og_image = movie.poster_image.url if movie.poster_image else request.build_absolute_uri(static('assets/img/postal.jpg'))

    movie_schema = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "name": movie.title,
        "description": movie.description,
        "image": og_image,
        "datePublished": f"{movie.release_year}-01-01",
        "genre": [genre.name for genre in movie.genre.all()] if movie.genre.exists() else ["Unknown"],
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": movie.views.count(),  # Replace with actual rating if available
            "ratingCount": movie.views.count()
        }
    }

    return render(request, 'account/manualview.html', {
        'movie': movie, 
        'comments': page_obj, 
        'page_obj': page_obj,
        'seo_title': seo_title, 
        'seo_description': seo_description,
        'canonical_url': request.build_absolute_uri(),
        'seo_robots': seo_robots,
        'prev_page_url': request.build_absolute_uri(f"?page={int(page) - 1}") if page_obj.has_previous() else None,
        'next_page_url': request.build_absolute_uri(f"?page={int(page) + 1}") if page_obj.has_next() else None,
        'movie_schema': movie_schema,
        'og_title': seo_title,
        'og_description': seo_description,
        'og_image': og_image,
        'og_url': request.build_absolute_uri(),
    })


@login_required
def like_comment1(request, comment_id):
    comment = get_object_or_404(Commentmovie, id=comment_id)
    user = request.user

    if user in comment.liked_by.all():
        # User already liked, so remove the like
        comment.liked_by.remove(user)
        comment.likes -= 1
    elif user in comment.disliked_by.all():
        # User disliked, so switch to like
        comment.disliked_by.remove(user)
        comment.dislikes -= 1
        comment.liked_by.add(user)
        comment.likes += 1
    else:
        # New like
        comment.liked_by.add(user)
        comment.likes += 1

    comment.save()
    return JsonResponse({
        'status': 'success',
        'likes': comment.likes,
        'dislikes': comment.dislikes
    })

@login_required
def dislike_comment1(request, comment_id):
    comment = get_object_or_404(Commentmovie, id=comment_id)
    user = request.user

    if user in comment.disliked_by.all():
        # User already disliked, so remove the dislike
        comment.disliked_by.remove(user)
        comment.dislikes -= 1
    elif user in comment.liked_by.all():
        # User liked, so switch to dislike
        comment.liked_by.remove(user)
        comment.likes -= 1
        comment.disliked_by.add(user)
        comment.dislikes += 1
    else:
        # New dislike
        comment.disliked_by.add(user)
        comment.dislikes += 1

    comment.save()
    return JsonResponse({
        'status': 'success',
        'likes': comment.likes,
        'dislikes': comment.dislikes
    })


from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError
from django.template import loader
from django.core.exceptions import PermissionDenied

# Custom error views
def custom_bad_request(request, exception):
    return render(request, '400.html', status=400)

def custom_permission_denied(request, exception):
    return render(request, '403.html', status=403)

def custom_page_not_found(request, exception):
    return render(request, '404.html', status=404)

def custom_server_error(request):
    return render(request, '500.html', status=500)
