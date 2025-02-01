from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm, UserRegisterForm
from bus.models import User
from django.contrib.auth import login
from .utils import generate_otp, verify_otp
from django.core.mail import send_mail
from django.conf import settings

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'users/profile.html', context)

def register(request):
    form=UserRegisterForm()
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            user =User.objects.create_user(username=username, email=email, password=password)
            email_otp = generate_otp()
            user.email_otp = email_otp
            user.save()
            send_mail(
                'Email Verification OTP',
                f'Your OTP for email verification is: {email_otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success(request, f'Your account has been created.')
            return redirect('verify_otp', user_id=user.id)
        

    return render(request, 'users/register.html',{'form': form})


def verif_otp(request, user_id):
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        email_otp = request.POST['email_otp']
        if verify_otp(email_otp, user.email_otp):
            user.is_email_verified = True
            user.email_otp = None
            user.save()
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'users/verify_otp.html', {'error': 'Invalid OTP'})

    return render(request, 'users/verify_otp.html')