from .forms import RegisterForm, UserChangeForm, UserAdminCreationForm
from django.shortcuts import render_to_response, get_object_or_404
from django.urls import reverse_lazy
from django.views import generic
from .models import MyUser


class SignUp(generic.CreateView):
    form_class = UserAdminCreationForm
    # user_profile_form_class = UserForm
    success_url = reverse_lazy('login')
    template_name = 'accounts/signup.html'


class UserProfileUpdateView(generic.UpdateView):
    # context_object_name = 'user_update'
    model = MyUser
    form_class = UserChangeForm
    template_name = "accounts/update.html"
    success_url = reverse_lazy('question_list')

    def get_object(self, queryset=None):
        return self.request.user
