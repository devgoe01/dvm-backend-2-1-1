# REQUEST.SESSION

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm, UserRegisterForm,AddBalanceForm
from bus.models import User
from django.contrib.auth import login
from .utils import generate_otp, verify_otp
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


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
#    if request.user.is_authenticated:
#        return redirect('dashboard')
    form = UserRegisterForm()
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            email_otp = generate_otp()
            
            request.session['temp_user'] = {'username': username,'email': email,
            'password': password,'otp': email_otp,
            'otp_creation_time': timezone.now().isoformat(),'otp_resend_attempts' : 1,}

            '''
            last_resend_time = timezone.datetime.fromisoformat('otp_creation_time')
            cooldown_period = timedelta(seconds=30)
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP.")
                return redirect('register')
            otp_resend_attempts = request.session.get('otp_resend_attempts', 0)
            max_resend_attempts = 5
            if otp_resend_attempts >= max_resend_attempts and timezone.now() - last_resend_time < timedelta(minutes=5):
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.")
                return redirect('register')
            '''
            send_mail(
                'Email Verification OTP',
                f'Your OTP for email verification is: {email_otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            messages.success (request, "An OTP has been sent to your email.")
            return redirect('verif_otp')

    return render(request, 'users/register.html', {'form': form})



def verif_otp(request):
    temp_user = request.session.get('temp_user')
# insures that if a person is visiting the page without going through the registration process, they are redirected to the register page
    if not temp_user:
        messages.error(request, "Please register again.")
        return redirect('register')
    stored_otp=temp_user['otp']
    otp_creation_time=temp_user['otp_creation_time']
    username=temp_user['username']
    password=temp_user['password']
    email=temp_user['email']
    otp_resend_attempts = temp_user['otp_resend_attempts']
    last_resend_time = timezone.datetime.fromisoformat(temp_user['otp_creation_time'])
    if request.method == 'POST':
        entered_otp = request.POST.get('email_otp')
        if entered_otp.lower() == 'resend':
            cooldown_period = timedelta(seconds=30)
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP.")
                return redirect('verif_otp')
            
            max_resend_attempts = 5
            if otp_resend_attempts >= max_resend_attempts:
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.Try registering again after some time")
                return redirect('verif_otp')
            
            new_otp = generate_otp()
            temp_user['otp'] = new_otp
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            temp_user['otp_resend_attempts'] = otp_resend_attempts + 1
            temp_user['otp_creation_time'] = timezone.now().isoformat()
            messages.success(request, "A new OTP has been sent to your email.")
            request.session['temp_user'] = temp_user
            return redirect('verif_otp')
        if verify_otp(entered_otp,stored_otp):
            otp_creation_time = timezone.datetime.fromisoformat(otp_creation_time)
            if (timezone.now() - otp_creation_time) > timedelta(minutes=2):
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verif_otp')
            user = User.objects.create_user(username=username,email=email,password=password)
            user.save()
            send_mail(
                'Account Created Successfully',
                f'Congratulations {user.username}, you have been signed up for our bus booking platform!',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
            del request.session['temp_user']
            login(request, user)
            messages.success(request, "Your account has been created successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'users/verify_otp.html')
    return render(request, 'users/verify_otp.html')

@login_required
def add_balance(request):
    if request.method == 'POST':
        form=AddBalanceForm(request.POST)
        if form.is_valid():
            user=request.user
            amount=form.cleaned_data['Add_amount']
            user.wallet_balance+=amount
            user.save()
            messages.success(request, "Balance added successfully!")
            try:
                send_mail(
                    'Balance Added',
                    f'{amount} rupees have been successfully added to your account.\n Your balance has been added successfully! Your new balance is: {user.wallet_balance} rupees.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
            except:
                pass
            return redirect('dashboard')
    return render(request, 'users/add_balance.html',{'form':AddBalanceForm()})