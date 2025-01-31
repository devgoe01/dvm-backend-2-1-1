from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Skip sign-up if user already exists
        if sociallogin.is_existing:
            return redirect('dashboard')  # Replace 'dashboard' with the name of your login redirect URL
