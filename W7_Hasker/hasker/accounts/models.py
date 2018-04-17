from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)
from django.urls import reverse
from django.utils.safestring import mark_safe


class MyUserManager(BaseUserManager):
    def create_user(self, email, login, avatar, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        if not login:
            raise ValueError('Users must have login')

        user = self.model(
            email=self.normalize_email(email),
            login=login,
            avatar=avatar,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, login, avatar, password):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            login=login,
            password=password,
            avatar=avatar,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    login = models.CharField(max_length=255, unique=True,)
    avatar = models.ImageField(upload_to='static/avatars/')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['avatar', 'email']

    def __str__(self):
        return self.login

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    def get_absolute_url(self):
        return reverse('user_profile', kwargs={'slug': self.login})

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin