from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Video
from django.contrib.auth.decorators import login_required
from .vidmaker import parse_prompt_from_url, parse_prompt
from django.conf import settings
from django import forms

@login_required
def video_list(request):
    videos = Video.objects.all()
    return render(request, 'videos/video_list.html', {'videos': videos})

@login_required
def video_detail(request, video_id):
    video = get_object_or_404(Video, pk=video_id)
    return render(request, 'videos/video_detail.html', {'video': video})

class PromptUrlForm(forms.Form):
    openai_key = forms.CharField(
        label='OpenAI API key',
        required=False,
        help_text='Requesting an OpenAI API key is explained in <a href="https://platform.openai.com/docs/quickstart/step-2-setup-your-api-key">the OpenAPI docs</a>.'
    )
    prompt_url = forms.CharField(
        label='Prompt url',
        required=False,
        help_text='A website link with an article for generating a video message (such as a wikipedia article).'
    )

    def __init__(self, *args, **kwargs):
        openai_key_set = kwargs.pop('openai_key_set', False)
        super(PromptUrlForm, self).__init__(*args, **kwargs)
        if openai_key_set:
            self.fields.pop('openai_key')

@login_required
def video_generator(request):
    if request.method == 'POST':
        form = PromptUrlForm(request.POST)
        if form.is_valid():
            prompt_url = form.cleaned_data['prompt_url']
            initial = {'api_prompt': parse_prompt_from_url(prompt_url)}
            openai_key = form.cleaned_data['openai_key']
            if settings.OPENAI_API_KEY == None and openai_key:
                initial['openai_key'] = openai_key
            form = PromptForm(openai_key_set=settings.OPENAI_API_KEY != None,
                              initial=initial)
            return render(request, 'videos/video_prompt.html', {'form': form})
    else:
        form = PromptUrlForm(openai_key_set=settings.OPENAI_API_KEY != None)

    return render(request, 'videos/video_generator.html', {'form': form})

class PromptForm(forms.Form):
    openai_key = forms.CharField(
        label='OpenAI API key',
        required=False,
        help_text='Requesting an OpenAI API key is explained in <a href="https://platform.openai.com/docs/quickstart/step-2-setup-your-api-key">the OpenAPI docs</a>.'
    )
    api_prompt = forms.CharField(
        label='Prompt',
        widget=forms.Textarea(attrs={'rows': 30, 'cols': 80}),
        help_text='Designate prompt sections by spliting them up by two newlines (\'\\n\\n\').',
        required=True
    )
    age = forms.IntegerField(
        label='Audience age',
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={'type': 'number'}),
        help_text='The age the generated video will be geared towards.',
        initial=10
    )

    def __init__(self, *args, **kwargs):
        openai_key_set = kwargs.pop('openai_key_set', False)
        super(PromptForm, self).__init__(*args, **kwargs)
        if openai_key_set:
            self.fields.pop('openai_key')

@login_required
def video_prompt(request):
    if request.method == 'POST':
        form = PromptForm(request.POST)
        if form.is_valid():
            openai_key = form.cleaned_data['openai_key']
            age = form.cleaned_data['age']
            if not openai_key:
                openai_key = settings.OPENAI_API_KEY
            api_prompt = form.cleaned_data['api_prompt']
            prompts = parse_prompt(openai_key, api_prompt, age)
            initial = { 'prompt%d' % i: prompts[i] for i in range(0, len(prompts))}
            form = PromptsForm(openai_key_set=settings.OPENAI_API_KEY != None,
                              initial=initial, num_prompts=len(prompts))
            return render(request, 'videos/video_prompts.html', {'form': form})

class PromptsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        openai_key_set = kwargs.pop('openai_key_set', False)
        if openai_key_set:
            self.fields.pop('openai_key')
        num_prompts = kwargs.pop('num_prompts', 0)
        super(PromptsForm, self).__init__(*args, **kwargs)
        for i in range(0, num_prompts):
            self.fields['prompt%d' % i] = forms.CharField(
                label='',
                widget=forms.Textarea(attrs={'rows': 6, 'cols': 80}),
                required=True
            )

@login_required
def video_prompts(request):
    if request.method == 'POST':
        pass
