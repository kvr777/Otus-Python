from django.urls import path

from . import views


urlpatterns = [
    path('signup/', views.SignUp.as_view(), name='signup'),
    path('<slug:login>/', views.UserProfileUpdateView.as_view(), name='user_profile')
]