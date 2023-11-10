from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_list, name='video_list'),
    path('<int:video_id>/', views.video_detail, name='video_detail'),
    path('new/', views.video_generator, name='video_generator'),
    path('prompt/', views.video_prompt, name='video_prompt'),
    path('segments/', views.video_prompts, name='video_prompts')
]
