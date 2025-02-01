from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from .models import User,Route,Bus,Booking
from django.contrib import messages
from .forms import SearchForm,BookingForm,EditBookingForm,EditBusForm
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
from users import utils

@login_required
def dashboard(request):
    if request.user.role == 'admin' or request.user.role=='Administrator':
        return render(request,'bus/admin_dashboard.html')
    else:
        return render(request,'bus/passenger_dashboard.html')

def home(request):
    buses=None
    if request.method == "GET":
        form=SearchForm(request.GET)
        if form.is_valid():
            source=form.cleaned_data['source']
            destination=form.cleaned_data['destination']
            buses=Bus.objects.filter(route__source__icontains=source,route__destination__icontains=destination)
            sort_by_departure=form.cleaned_data['sort_by_departure']
            if sort_by_departure:
                buses=buses.order_by('departure_time')
            else:
                buses=buses.order_by('-available_seats')
    else:
        form=SearchForm()
    return render(request, 'bus/home.html', {'form': form, 'buses': buses})

@login_required
def book_bus(request, bus_number):
    bus=get_object_or_404(Bus, bus_number=bus_number)
    if request.method == "POST":
        form=BookingForm(request.POST)
        form.instance.bus=bus
        user=request.user
        if form.is_valid():
            booking=form.save(commit=False)
            booking.user=request.user
            booking.bus=bus
            seats_booked=form.cleaned_data['seats_booked']
            if user.wallet_balance >= (seats_booked * bus.fare):
                email_otp = utils.generate_otp()
                request.session['temp_booking'] = {'bus_number': booking.bus.bus_number,'seats_booked': seats_booked,'otp': email_otp}
            
                send_mail(
                    'Email Verification OTP',
                    f'Your OTP for email verification is: {email_otp}',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )
                return redirect('verif_bus_otp')
            else:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('book_bus', bus_number=bus_number)
        else:
            messages.error(request, "Not enough seats available.")
                
    else:
        form=BookingForm()

    return render(request, 'bus/book_bus.html', {'form': form, 'bus': bus})


def verif_bus_otp(request):
    temp_booking = request.session.get('temp_booking')

    if not temp_booking:
        messages.error(request, "Please try again.")
        return redirect('project-home')

    if request.method == 'POST':
        entered_otp = request.POST.get('email_otp')
        stored_otp = temp_booking['otp']

        if entered_otp=="Resend" or entered_otp=="resend" or entered_otp=="ReSend" or entered_otp=="RESEND":
            new_otp = utils.generate_otp()
            temp_booking['otp'] = new_otp
            request.session['temp_user'] = temp_booking
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [temp_booking['email']],
                fail_silently=False,
            )
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verif_bus_otp')
        if utils.verify_otp(entered_otp,stored_otp):
            user = request.user
            bus = get_object_or_404(Bus,bus_number=temp_booking['bus_number'])
            seats_booked = temp_booking['seats_booked']
            booking = Booking.objects.create(user=request.user,bus=bus,seats_booked=seats_booked)
            booking.save()
            user.wallet_balance -= (seats_booked * bus.fare)
            user.save()
            bus.available_seats -= seats_booked
            bus.save()
            booking.save()
            messages.success(request, "Your booking was successful!")
            send_mail(
            f'You booking for bus {bus.bus_number} has been confirmed!',
            f'Congratulations {user.username}, you booked {seats_booked} seats for bus {bus.bus_number} from {bus.route.source} to {bus.route.destination} on {booking.booking_time.strftime("%A, %B %d, %Y, %I:%M %p")}.\n{seats_booked*bus.fare} rupees has been debited from your wallet. Your current remaining balance is {user.wallet_balance} rupees.\nYour booking id is {booking.id}.\nDeparture time for bus is {bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False)
            del request.session['temp_booking']
            return redirect('booking_summary')
        else:
            return render(request, 'users/verify_otp.html', {'error': 'Invalid OTP'})

    return render(request, 'users/verify_otp.html')

@login_required
def booking_summary(request):
    bookings=Booking.objects.filter(user=request.user)
    confirmed_bookings=(bookings.filter(status='Confirmed',user=request.user)).count()
    if (not confirmed_bookings):
        confirmed_bookings='no'
    for booking in bookings:
        time_remaining=(booking.bus.departure_time - now()).total_seconds() /(60*60)
        booking.can_edit=time_remaining > 6
    context={'bookings':bookings,'confirmed_bookings':confirmed_bookings}
    return render(request, 'bus/booking_summary.html', context)


@login_required
def edit_booking(request, booking_id):
    booking=get_object_or_404(Booking, id=booking_id, user=request.user)
    time_remaining=(booking.bus.departure_time - now()).total_seconds() / 3600
    original_seats_booked=booking.seats_booked
    if time_remaining < 6:
        messages.error(request, "You cannot edit this booking as there are less than 6 hours left before departure.")
        return redirect('booking_summary')
    if booking.status == 'Cancelled':
        messages.error(request, "You cannot edit this booking as it has been cancelled.")
        return redirect('booking_summary')
    if request.method == "POST":
        form=EditBookingForm(request.POST,instance=booking)
        if form.is_valid():
            updated_booking=form.save(commit=False)
            if updated_booking.status == 'Cancelled' or updated_booking.seats_booked==0:
                updated_booking.status='Cancelled'
                request.user.wallet_balance +=booking.seats_booked * booking.bus.fare
                request.user.save()
                booking.bus.available_seats += booking.seats_booked
                booking.bus.save()
            difference=updated_booking.seats_booked - original_seats_booked
            if difference!=0:
                additional_cost=difference * booking.bus.fare
                if request.user.wallet_balance >= additional_cost:
                    request.user.wallet_balance -= additional_cost
                    request.user.save()
                    booking.bus.available_seats -= difference
                    booking.bus.save()
                    send_mail(
                    f'Updated booking status for bus {booking.bus.bus_number}',
                    f'Booking status for bus {booking.bus.bus_number} has been updated.\n{updated_booking.seats_booked} seats are booked for bus {booking.bus.bus_number} from {booking.bus.route.source} to {booking.bus.route.destination} \n{additional_cost} rupees has been debited from your wallet. Your current remaining balance is {request.user.wallet_balance} rupees.\nYour booking id is {booking.id}.\n Departure time for bus is {booking.bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
                    settings.EMAIL_HOST_USER,
                    [request.user.email],
                    fail_silently=False)
                    updated_booking.save()
                    messages.success(request, "Booking updated successfully!")
                    return redirect('booking_summary')
                else:
                    messages.error(request, "Insufficient wallet balance for additional seats.")
                    return redirect('edit_booking', booking_id=booking_id)
            else:
                messages.error(request, "No change in number of seats.")
                return redirect('edit_booking', booking_id=booking_id)
    else:
        form=EditBookingForm(instance=booking, current_booking=booking)

    return render(request, 'bus/edit_booking.html', {'form': form, 'booking': booking})
            
def about(request):
    return render(request, 'bus/about.html', {'title': 'About'})


@login_required
def edit_bus(request, bus_number):
    bus = get_object_or_404(Bus, bus_number=bus_number)
    if (not request.user.is_authenticated) or (request.user.role=='passenger' or request.user.role=='Passenger'):
        messages.error(request, "You do not have permission to edit buses.")
        return redirect('dashboard')

    if (request.user.role=='admin' or request.user.role=='Administrator') and (not request.user.can_change_buses.filter(bus_number=bus_number).exists()):
        messages.error(request, "You are not authorized to edit this bus.")
        return redirect('dashboard')
    
    if request.method == "POST":
        form = EditBusForm(request.POST, instance=bus)
        if form.is_valid():
            form.save()
            messages.success(request, "Bus updated successfully!")
            return redirect('dashboard')
    else:
        form = EditBusForm(instance=bus)
    return render(request, 'bus/edit_bus.html', {'form': form, 'bus': bus})

def admin_bus_list(request):
    user=request.user
    if (not request.user.is_authenticated) or (request.user.role=='passenger' or request.user.role=='Passenger'):
        messages.error(request, "You do not have permission to edit buses.")
        return redirect('dashboard')
    buses = request.user.can_change_buses.all()
    print(buses)
    return render(request, 'bus/bus_list.html', {'buses': buses})