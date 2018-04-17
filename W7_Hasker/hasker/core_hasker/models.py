from django.db import models
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import re
from .utils import unique_slugify, pretty_date


class Question(models.Model):
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=255)
    question_tags = models.CharField(max_length=200)
    question_text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    positive_votes = models.IntegerField(default=0)
    negative_votes = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)

    def __unicode__(self):
        return self.title

    @property
    def get_trending(self):
        return self.order_by('-total_points', '-created_at')[:2]

    def get_date(self):
        return pretty_date(self.created_at)


    def get_tag_list(self):
        return re.split(" ", self.question_tags)

    def save(self, *args, **kwargs):
        slug = self.title
        unique_slugify(self, slug)
        self.total_points = self.positive_votes - self.negative_votes
        super(Question, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('question_detail', kwargs={'slug': self.slug})


class QuestionVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'question')


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    positive_votes = models.IntegerField(default=0)
    negative_votes = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.total_points = self.positive_votes - self.negative_votes
        super(Answer, self).save(*args, **kwargs)

    def __unicode__(self):
        return u"id: %s question: %s text: %s " % (
            self.id, self.question, self.answer_text[:100])


class AnswerVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    value = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'answer')
