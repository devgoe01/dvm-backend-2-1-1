from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        This method is called before the social login flow completes.
        It checks if a user with the same email already exists and links the
        social account to that user.
        """
        # Get the email from the social account
        email = sociallogin.account.extra_data.get('email')

        if not email:
            # If no email is provided, stop the process (optional)
            raise ImmediateHttpResponse(redirect('custom-error-page'))  # Replace with your error page

        try:
            # Check if a user with this email already exists
            user = User.objects.get(email=email)
            sociallogin.connect(request, user)  # Link the social account to the existing user
        except User.DoesNotExist:
            # If no user exists with this email, proceed with the default behavior (sign-up)
            pass
