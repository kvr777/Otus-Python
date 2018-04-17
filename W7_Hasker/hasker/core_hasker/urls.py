from django.urls import path, include
from .views import QuestionListView, QuestionDetailView, \
    QuestionCreateView, QuestionSearchListView,AnswerCreateView, QuestionVoteView, \
    AnswerVoteView, error_404

urlpatterns = [path('', QuestionListView.as_view(),
                   name='question_list'),
               path('question/<slug:slug>', QuestionDetailView.as_view(),
                    name='question_detail'),
               path('new_question/', QuestionCreateView.as_view(),
                    name='new_question'),
               path('search/', QuestionSearchListView.as_view(),
                   name='question_search_list_view'),
               path('add_answer/<slug:slug>',
                           AnswerCreateView.as_view(), name='add_answer'),
               path ('vote/question/<int:object_id>',
                  QuestionVoteView.as_view(), name='question_vote'),

                path ('vote/answer/<int:object_id>',
                  AnswerVoteView.as_view(), name='answer_vote'),

               ]

handler404 = error_404