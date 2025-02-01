from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from django.conf import settings
from django.contrib.auth import get_user_model

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    
    class Meta:
        model = get_user_model()
        fields = ['username', 'email','password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = get_user_model()
        fields = ['username', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
