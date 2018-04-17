from django import forms
from .models import Question, Answer


class QuestionCreateForm(forms.ModelForm):

    class Meta:
        model = Question
        fields = ['title', 'question_text', 'question_tags']

        labels = {
            'title': 'Title:',
            'question_text': 'Question detail:',
        }

    question_tags = forms.CharField(label='Tags:', widget=forms.TextInput(attrs={'Placeholder': 'tag1 tag2 tag3'}))

    def clean(self):
        tags = self.cleaned_data['question_tags']
        if len(tags.split())>3:
            raise forms.ValidationError("You cannot assign more than 3 tags")
        return self.cleaned_data


class AnswerCreateForm(forms.ModelForm):

    class Meta:
        model = Answer
        fields = ['answer_text']

        labels = {
            'answer_text': '',
        }


    def __init__(self, author, current_question, *args, **kwargs):
        super(AnswerCreateForm, self).__init__(*args, **kwargs)
        self.author = author
        self.question = current_question

    def clean(self):
        if Answer.objects.filter(question=self.question, author=self.author):
            raise forms.ValidationError("You've asked already on this question")
        return self.cleaned_data

