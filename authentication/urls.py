
from django.urls import path
from . import views

from django.views.generic.base import TemplateView
from django.contrib.sitemaps.views import sitemap
from authentication.sitemaps import StaticSitemap, TMDBMovieSitemap, ManualMovieSitemap  # Import from your app

app_name = 'auth'


sitemaps = {
    'static': StaticSitemap,
    'tmdb_movies': TMDBMovieSitemap,
    'manual_movies': ManualMovieSitemap,
}

urlpatterns = [
    path('metculture/', views.metculture, name='metculture'),
    path('login/', views.login_view, name='account_login'),
    path('signup/', views.signup_view, name='account_signup'),
    path('logout/', views.logout, name='logout'),
    path('', views.index_view, name='home_view'),
    path('upcoming/', views.upcoming_movies, name='upcoming_movies'),
    path('popular/', views.popular_movies, name='popular_movies'),
    path('localmovies/', views.manual_movies, name='manual_movies'),
    path('movie/<slug:slug>/', views.movie_detail, name='movie_detail'),
    path('manual-movie/<slug:slug>/', views.manual_movie_detail, name='movie_detail1'),
    # path('movies/<int:movie_id>/', views.manual_movie_detail, name='movie_detail1'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/dislike/', views.dislike_comment, name='dislike_comment'),

    path('commentmanual/<int:comment_id>/like/', views.like_comment1, name='like_comment1'),
    path('commentmanual/<int:comment_id>/dislike/', views.dislike_comment1, name='dislike_comment1'),
    path('all/', views.all_movies, name='all_movies'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]
