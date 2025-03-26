from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email')

        if not email:
            raise ImmediateHttpResponse(redirect('custom-error-page'))

        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass

#from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
#
#class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#    def get_connect_redirect_url(self, request, socialaccount):
#        return '/dashboard/'