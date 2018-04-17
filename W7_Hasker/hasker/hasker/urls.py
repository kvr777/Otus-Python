"""hasker URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views
from django.contrib.auth.views import logout
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', views.LoginView.as_view(redirect_authenticated_user=True,
        template_name="accounts/login.html"), name='login'),
    path('', include('core_hasker.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', logout, {'next_page':settings.LOGOUT_REDIRECT_URL}, name='logout')

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
