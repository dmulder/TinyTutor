#!/usr/bin/python3
from openai import OpenAI, InternalServerError, RateLimitError
from mutagen.mp3 import MP3
from moviepy import editor
import os
import requests
from tempfile import NamedTemporaryFile
import validators
from urllib.request import urlopen
from bs4 import BeautifulSoup
from time import sleep
import logging

class VideoBlock:
    def __init__(self, client, paragraph_input, logger):
        self.client = client
        self.text = paragraph_input
        self.logger = logger
        self.audio = None
        self.image = None
        self.video = None

    def choose_image(self, fname):
        # Is it a url, or a local filename?
        if validators.url(fname):
            img_data = requests.get(fname).content
            with NamedTemporaryFile('w', delete=False) as t:
                self.image = t.name
            with open(self.image, 'wb') as w:
                w.write(img_data)
        elif os.path.exists(fname):
            self.image = fname

    def generate_image(self):
        # Generate images until the user decides it is sufficient
        try:
            response = self.client.images.generate(
              model="dall-e-3",
              prompt='Digital art that envisions the following prompt: "%s"' % self.text,
              size="1792x1024",
              quality="standard",
              n=1,
            )
        except (InternalServerError, RateLimitError):
            self.logger.error('Image failed to generate')
            return
        image_url = response.data[0].url
        img_data = requests.get(image_url).content
        with NamedTemporaryFile('w', delete=False, suffix='.png') as t:
            self.image = t.name
        with open(self.image, 'wb') as w:
            w.write(img_data)

    def generate_audio(self):
        # Generate the spoken audio
        try:
            response = self.client.audio.speech.create(
              model="tts-1",
              voice="alloy",
              input=self.text
            )
        except (InternalServerError, RateLimitError):
            self.logger.error('Audio failed to generate')
            return
        with NamedTemporaryFile('w', delete=False, suffix='.mp3') as t:
            response.stream_to_file(t.name)
            self.audio = t.name

    def generate_video(self):
        video = editor.ImageClip(self.image)
        audio = MP3(self.audio)
        audio_length = audio.info.length
        video.duration = audio_length
        audio = editor.AudioFileClip(self.audio)
        final_video = video.set_audio(audio)
        with NamedTemporaryFile('w', delete=False, suffix='.mp4') as t:
            self.video = t.name
        final_video.write_videofile(fps=1, codec="mpeg4", filename=self.video)

    def cleanup(self):
        if self.image:
            os.remove(self.image)
        if self.audio:
            os.remove(self.audio)

class VideoGenerator():
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._age = None
        self._openai_key = None

    def openai_key_set(self):
        return self._openai_key != None

    @property
    def openai_key(self):
        return self._openai_key

    @openai_key.setter
    def openai_key(self, value):
        self._openai_key = value
        self.client = OpenAI(api_key=self._openai_key)

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value

    def prompt_msg(self):
        if self._age != None:
            audiance_type = 'a child' if self._age < 18 else 'an adult'
            prompt_msg = 'Phrase your response for %s aged %d. ' % (audiance_type, self._age)
        else:
            prompt_msg = 'Phrase your response for a child. '
        return prompt_msg

    def parse_prompt_from_url(self, prompt_url):
        html = urlopen(prompt_url).read()
        soup = BeautifulSoup(html, features="html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        prompt = soup.get_text()
        while '\n\n\n' in prompt:
            prompt = prompt.replace('\n\n\n', '\n\n')
        self._prompt = prompt

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, value):
        self._prompt = value

    @prompt.deleter
    def prompt(self):
        del self._prompt

    def blocks(self):
        if not self._prompt:
            self.logger.error('No prompt was set when calling for video blocks!')
            return []
        # Split up the prompt by paragraph.
        self.final_content = []
        for prompt_paragraph in prompt.split('\n\n'):
            timeout = 0
            main_content = self._prompt_message(self.prompt_msg()+prompt_paragraph)
            # If the server failed to respond, wait a moment and try again
            while not main_content and timeout < 3:
                timeout += 1
                self.logger.warning('Server failed to respond, trying again in 5 seconds')
                sleep(5)
                main_content = self._prompt_message(self.prompt_msg()+prompt_paragraph)
            if not main_content:
                self.logger.error('Server failed to respond after 3 attempts, falling back to the input text')
                main_content = prompt_paragraph
            for content in main_content.split('\n\n'):
                self.final_content.append(VideoBlock(self.client, content, self.logger))
        return self.final_content

    def generate_video(self):
        self.logger.info('Generating audio')
        for content in self.final_content:
            content.generate_audio()
            timeout = 0
            while not content.audio and timeout < 3:
                timeout += 1
                self.logger.warning('Server failed to respond, trying again in 5 seconds')
                sleep(5)
                content.generate_audio()
            if not content.audio:
                self.logger.error('Server failed to respond after 3 attempts, video creation failed!')
                return None
        self.logger.info('Generating video')
        for content in self.final_content:
            content.generate_video()
        return self._append_videos()

    def _append_videos(self):
        with NamedTemporaryFile('w', delete=False, suffix='.mp4') as t:
            output_filename = t.name
        video_files = [editor.VideoFileClip(c.video) for c in self.final_content]
        final_clip = editor.concatenate_videoclips(video_files)
        final_clip.to_videofile(output_filename, fps=1)

        for content in self.final_content:
            content.cleanup()
        self.logger.info('Video created successfully!')
        return output_filename

    def _prompt_message(self, prompt):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-3.5-turbo",
            )
        except (InternalServerError, RateLimitError) as e:
            self.logger.error('Failed generating text: %s' % str(e))
            return None
        else:
            return chat_completion.choices[0].message.content

def parse_prompt_from_url(prompt_url):
    html = urlopen(prompt_url).read()
    soup = BeautifulSoup(html, features="html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    prompt = soup.get_text()
    while '\n\n\n' in prompt:
        prompt = prompt.replace('\n\n\n', '\n\n')
    return prompt
