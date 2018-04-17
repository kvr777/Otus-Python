from django.contrib import admin

from .models import Question, Answer


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    prepopulated_fields = {'slug': ('title',)}


class AnswerAdmin(admin.ModelAdmin):
    pass


class SavedQuestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'question',)


class QuestionTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
# admin.site.register(SavedQuestionAdmin)
# admin.site.register(QuestionTag, QuestionTagAdmin)