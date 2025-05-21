from django.urls import path
from . import views

urlpatterns = [
    path('video-call/<str:username>/', views.video_call, name='video_call'),
]