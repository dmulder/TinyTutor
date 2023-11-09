from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Video
from django.contrib.auth.decorators import login_required
from .vidmaker import VideoGenerator
from django.conf import settings

@login_required
def video_list(request):
    videos = Video.objects.all()
    return render(request, 'videos/video_list.html', {'videos': videos})

@login_required
def video_detail(request, video_id):
    video = get_object_or_404(Video, pk=video_id)
    return render(request, 'videos/video_detail.html', {'video': video})

@login_required
def video_generator(request):
    generator = VideoGenerator()
    if settings.OPENAI_API_KEY != None:
        generator.openai_key = settings.OPENAI_API_KEY
    return render(request, 'videos/video_generator.html', {'generator': generator})
