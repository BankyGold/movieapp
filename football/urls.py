
from django.urls import path
from . import views

app_name = 'foot'

urlpatterns = [
    path('', views.video_list, name='video_list'),
    path('video/<str:video_id>/', views.video_detail, name='video_detail'),
]
