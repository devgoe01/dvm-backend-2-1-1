from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from .models import User,Route,Bus,Booking,Waitlist
from django.contrib import messages
from .forms import SearchForm,BookingForm,EditBookingForm,EditBusForm,AddBusForm
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
from users import utils
from django.utils import timezone
from datetime import timedelta
import openpyxl
from django.http import HttpResponse
from .utils import unpack_available_seats_classes,unpack_booked_seats_class,pack_available_seats_classes,pack_booked_seats
#from .utils import unpack_seat_classes,pack_seat_classes
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
    available_seats=unpack_available_seats_classes(bus_number)
    total_available=0.5*sum(available_seats.values())
    if request.method == "POST":
        form=BookingForm(request.POST)
        form.instance.bus=bus
        user=request.user
        if form.is_valid():
            booking=form.save(commit=False)
            booking.user=user
            booking.bus=bus
            seats_booked=form.cleaned_data['seats_booked']
            for i in range(0,3):
                if seats_booked > list(available_seats.values())[i]:
                    waitlist=Waitlist.objects.create(user=user,bus=bus,seats_requested=seats_booked)
                    waitlist.save()
                    messages.info(request,"not available.You are in the waitlist .We will email you once seats are available.")
                    return redirect('booking_summary')
            selected_class=form.cleaned_data['seat_class']
            if seats_booked>available_seats[selected_class]:
                messages.error(request, "not enough available seats in this class.Try to book in different class.W")
                return redirect('book_bus', bus_number=bus_number)
            if user.wallet_balance >= (seats_booked * bus.fare):
                email_otp = utils.generate_otp()
                request.session['temp_booking'] = {'bus_number': booking.bus.bus_number,'seats_booked': seats_booked,'otp': email_otp,'otp_creation_time': timezone.now().isoformat(),'otp_resend_attempts' : 1,
                'selected_class': selected_class}
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
            messages.error(request, "Invalid form.")
            form=BookingForm()               
    else:
        form=BookingForm()

    return render(request, 'bus/book_bus.html', {'form': form, 'bus': bus})


def verif_bus_otp(request):
    temp_booking = request.session.get('temp_booking')
    entered_otp = request.POST.get('email_otp')
    stored_otp = temp_booking['otp']
    email=request.user.email
    selected_class=temp_booking['selected_class']
    seats_booked=temp_booking['seats_booked']
    otp_resend_attempts = temp_booking['otp_resend_attempts']
    last_resend_time = timezone.datetime.fromisoformat(temp_booking['otp_creation_time'])
    otp_creation_time = timezone.datetime.fromisoformat(temp_booking['otp_creation_time'])
    bus_number=temp_booking['bus_number']
    if not temp_booking:
        messages.error(request, "Please try again.")
        return redirect('project-home')
    if request.method == 'POST':
        if entered_otp.lower()=='resend':
            cooldown_period = timedelta(seconds=30)
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP. Try booking again after some time.")
                return redirect('verif_bus_otp')
            max_resend_attempts = 5
            if otp_resend_attempts >= max_resend_attempts:
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.")
                return redirect('verif_bus_otp')
            
            new_otp = utils.generate_otp()
            temp_booking['otp'] = new_otp
            temp_booking['otp_creation_time'] = timezone.now().isoformat()
            request.session['temp_booking'] = temp_booking
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            temp_booking['otp_resend_attempts'] = otp_resend_attempts + 1
            temp_booking['otp_creation_time'] = timezone.now().isoformat()
            request.session['temp_booking'] = temp_booking
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verif_bus_otp')
        if utils.verify_otp(entered_otp,stored_otp):
            if (timezone.now() - otp_creation_time) > timedelta(minutes=2):
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verif_bus_otp')
            user = request.user
            bus = get_object_or_404(Bus,bus_number=bus_number)
            user.wallet_balance -= (seats_booked * bus.fare)
            available_seats=unpack_available_seats_classes(bus_number)
            available_seats[selected_class] -= seats_booked
            bus.available_seats =pack_available_seats_classes(selected_class,available_seats[selected_class],bus_number)
            seats_booked_for_mail=seats_booked
            seats_booked=pack_booked_seats(selected_class,seats_booked)
            booking = Booking.objects.create(user=request.user,bus=bus,seats_booked=seats_booked)
            booking.save()
            user.save()
            bus.save()
            booking.save()
            messages.success(request, "Your booking was successful!")
            send_mail(
            f'You booking for bus {bus.bus_number} has been confirmed!',
            f'Congratulations {user.username}, you booked {seats_booked_for_mail} seats for bus {bus.bus_number} from {bus.route.source} to {bus.route.destination} on {booking.booking_time.strftime("%A, %B %d, %Y, %I:%M %p")}.\n{seats_booked_for_mail*bus.fare} rupees has been debited from your wallet. Your current remaining balance is {user.wallet_balance} rupees.\nYour booking id is {booking.id}.\nDeparture time for bus is {bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False)
            if (not temp_booking):
                del request.session['temp_booking']
            return redirect('booking_summary')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'users/verify_otp.html')
    return render(request, 'users/verify_otp.html')

@login_required
def booking_summary(request):
    bookings=Booking.objects.filter(user=request.user).order_by('-booking_time')
    confirmed_bookings=(bookings.filter(status='Confirmed',user=request.user)).count()
    if (not confirmed_bookings):
        confirmed_bookings='no'
    for booking in bookings:
        time_remaining=(booking.bus.departure_time - now()).total_seconds() /(60*60)
        booking.can_edit=time_remaining > 6 
        seats_booked = unpack_booked_seats_class(booking.seats_booked)
        booking.seat_class=list(seats_booked.values())[0]
        booking.seats_booked=list(seats_booked.values())[2]
    
    context={'bookings':bookings,'confirmed_bookings':confirmed_bookings}
    return render(request, 'bus/booking_summary.html', context)


@login_required
def edit_booking(request, booking_id):
    booking=get_object_or_404(Booking, id=booking_id, user=request.user)
    time_remaining=(booking.bus.departure_time - now()).total_seconds() / 3600
    seats_booked=booking.seats_booked
    seats_booked=unpack_booked_seats_class(seats_booked)
    for i in range(0, len(seats_booked)):
        if list(seats_booked.values())[i]:
            selected_class=list(seats_booked.keys())[i]
            break
    original_seats_booked=seats_booked['seats_booked']
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
            new_seats_booked=form.cleaned_data.get('seats_booked')
            updated_booking.seats_booked=pack_booked_seats(selected_class,new_seats_booked)
            updated_booking=form.save(commit=False)
            if updated_booking.status == 'Cancelled' or new_seats_booked==0:
                updated_booking.status='Cancelled'
                request.user.wallet_balance +=original_seats_booked * booking.bus.fare
                request.user.save()
                available_seats=unpack_available_seats_classes(booking.bus.bus_number)
                available_seats[selected_class] += original_seats_booked
                booking.bus.available_seats=pack_available_seats_classes(selected_class,available_seats[selected_class],booking.bus.bus_number)
                booking.bus.save()
                updated_booking.seats_booked=pack_booked_seats(selected_class,original_seats_booked)
                try:
                    send_mail(
                        f'Booking cancelled for bus {booking.bus.bus_number} on {booking.booking_time.strftime("%A, %B %d, %Y, %I:%M %p")}',
                        f'Booking  for bus {booking.bus.bus_number} has been cancelled.\n{original_seats_booked * booking.bus.fare} rupees have been transferred to your wallet. Your updated balance is {request.user.wallet_balance} rupees.\n',
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False)
                except:
                    pass
                updated_booking.save()
            difference=int(new_seats_booked) - original_seats_booked
            if difference!=0 and updated_booking.status=='Confirmed':
                additional_cost=difference * booking.bus.fare
                if request.user.wallet_balance >= additional_cost:
                    request.user.wallet_balance -= additional_cost
                    request.user.save()
                    available_seats=unpack_available_seats_classes(booking.bus.bus_number)
                    available_seats[selected_class] -= difference
                    booking.bus.available_seats=pack_available_seats_classes(selected_class,available_seats[selected_class],booking.bus.bus_number)
                    booking.bus.save()
                    try:
                        send_mail(
                        f'Updated booking status for bus {booking.bus.bus_number} on {booking.bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}',
                        f'Booking status for bus {booking.bus.bus_number} has been updated.\n{new_seats_booked} seats are booked for bus {booking.bus.bus_number} from {booking.bus.route.source} to {booking.bus.route.destination} \n{additional_cost if (additional_cost>0) else (-1*additional_cost)} rupees have been {"deducted" if difference<0 else "added"} from your wallet. Your current remaining balance is {request.user.wallet_balance} rupees.\nYour booking id is {booking.id}.\n Departure time for bus is {booking.bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False)
                    except:
                        pass
                    updated_booking.seats_booked=pack_booked_seats(selected_class,new_seats_booked)
                    updated_booking.save()
                    messages.success(request, "Booking updated successfully!")
                    process_waitlist(booking.bus)
                    return redirect('booking_summary')
                else:
                    process_waitlist(booking.bus)
                    messages.error(request, "Insufficient wallet balance for additional seats.")
                    return redirect('edit_booking', booking_id=booking_id)
            elif difference==0:
                process_waitlist(booking.bus)
                messages.error(request, "No change in number of seats.")
                return redirect('edit_booking', booking_id=booking_id)
    else:
        form=EditBookingForm(instance=booking, current_booking=booking)
    
    seats_booked = unpack_booked_seats_class(booking.seats_booked)
    process_waitlist(booking.bus)
    booking.seat_class=list(seats_booked.values())[1]
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
            total_seats = form.cleaned_data['seat_classes']
            general,sleeper,luxury = map(int, total_seats.split('-'))
            total_seats=general+sleeper+luxury
            bus=form.save()
            bus.total_seats=total_seats
            bus.save()
            messages.success(request, "Bus updated successfully!")
            process_waitlist(bus)
            return redirect('dashboard')
    else:
        form = EditBusForm(instance=bus)
    return render(request, 'bus/edit_bus.html', {'form': form, 'bus': bus})

def admin_bus_list(request):
    if (not request.user.is_authenticated) or (request.user.role=='passenger' or request.user.role=='Passenger'):
        messages.error(request, "You do not have permission to edit buses.")
        return redirect('dashboard')
    buses = request.user.can_change_buses.all()
    return render(request, 'bus/bus_list.html', {'buses': buses})

@login_required
def export_buses_to_excel(request):
    if not request.user.is_authenticated or request.user.role.lower() == 'passenger':
        messages.error(request, "Sorry, you can't excess this page.")
        return redirect('dashboard')

    buses = request.user.can_change_buses.all()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Buses"

    headers = ['Bus Number', 'Route (Source)', 'Route (Destination)', 'Departure Time','Total Seats', 'Available Seats', 'Fare']
    sheet.append(headers)

    for bus in buses:
        row = [
            bus.bus_number,
            bus.route.source,
            bus.route.destination,
            bus.departure_time.strftime('%Y-%m-%d %H:%M:%S'),
            bus.total_seats,
            bus.available_seats,
            bus.fare,
        ]
        sheet.append(row)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="buses.xlsx"'
    workbook.save(response)
    return response




@login_required
def add_bus(request):
    if request.user.role.lower() != 'admin':
        messages.error(request, "You do not have permission to add buses.")
        return redirect('dashboard')

    if request.method == "POST":
        form = AddBusForm(request.POST)
        if form.is_valid():
            total_seats = form.cleaned_data['seat_classes']
            general,sleeper,luxury = map(int, total_seats.split('-'))
            total_seats=general+sleeper+luxury
            bus=form.save()
            bus.total_seats=total_seats
            bus.save()
            messages.success(request, "Bus added successfully!")
            request.user.can_change_buses.add(bus)
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AddBusForm()

    return render(request, 'bus/add_bus.html', {'form': form})


@login_required
def delete_bus(request, bus_number):
    try:
        bus = Bus.objects.get(bus_number=bus_number)
    except:
        messages.error(request, "Bus not found.")
        return redirect('dashboard')
    if request.user.role.lower() != 'admin' or bus not in request.user.can_change_buses.all():
        messages.error(request, "You do not have permission to delete this bus.")
        return redirect('dashboard')
    if request.method == "POST":
        email_otp = utils.generate_otp()
        request.session['temp_del'] = {'bus_number': bus_number,'otp': email_otp,'otp_creation_time': timezone.now().isoformat(),'otp_resend_attempts' : 1}
        send_mail(
            'OTP for verification',
            f'Your OTP is: {email_otp}',
            settings.EMAIL_HOST_USER,
            [request.user.email],
            fail_silently=False,
        )
        return redirect('verify_delete_bus_otp')

    return render(request, 'bus/delete_bus.html', {'bus': bus})


@login_required
def verif_del_bus_otp(request):
    temp_del = request.session.get('temp_del')
    entered_otp = request.POST.get('email_otp')
    stored_otp = temp_del['otp']
    otp_resend_attempts = temp_del['otp_resend_attempts']
    last_resend_time = timezone.datetime.fromisoformat(temp_del['otp_creation_time'])
    otp_creation_time = timezone.datetime.fromisoformat(temp_del['otp_creation_time'])
    bus_number=temp_del['bus_number']
    if not temp_del:
        messages.error(request, "Please try again.")
        return redirect('project-home')
    if request.method == 'POST':
        if entered_otp.lower()=='resend':
            cooldown_period = timedelta(seconds=30)
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP. Try booking again after some time.")
                return redirect('verify_delete_bus_otp')
            max_resend_attempts = 5
            if otp_resend_attempts >= max_resend_attempts:
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.")
                return redirect('verify_delete_bus_otp')
            
            new_otp = utils.generate_otp()
            temp_del['otp'] = new_otp
            temp_del['otp_creation_time'] = timezone.now().isoformat()
            request.session['temp_del'] = temp_del
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [request.user.email],
                fail_silently=False,
            )

            temp_del['otp_resend_attempts'] = otp_resend_attempts + 1
            temp_del['otp_creation_time'] = timezone.now().isoformat()
            request.session['temp_del'] = temp_del
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verify_delete_bus_otp')
        if utils.verify_otp(entered_otp,stored_otp):
            if (timezone.now() - otp_creation_time) > timedelta(minutes=2):
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verify_delete_bus_otp')
            bus=get_object_or_404(Bus,bus_number=bus_number)
            bookings = Booking.objects.filter(bus=bus)

            for booking in bookings:
                if booking.status == 'Confirmed':
                    user = booking.user
                    seats_booked = unpack_booked_seats_class(booking.seats_booked)
                    total_refund=booking.bus.fare*(list(seats_booked.values())[2])
                    user.wallet_balance +=total_refund
                    user.save()
#                       booking.status = 'Cancelled'
#                       booking.save()
                    try:
                        send_mail(
                            f'Booking Cancelled for Bus {bus.bus_number}',
                            f"Dear {user.username},\nYour booking for Bus {bus.bus_number} has been cancelled as the bus is no longer operational.\nA refund of {total_refund} rupees has been credited to your wallet. Your updated wallet balance is {user.wallet_balance} rupees.\nWe apologize for any inconvenience caused.\n",
                            settings.EMAIL_HOST_USER,[user.email],fail_silently=False,
                        )
                    except:
                        pass
            bus.delete()
            messages.success(request, f"Bus {bus.bus_number} deleted successfully!")
            if (not temp_del):
                del request.session['temp_del']
            return redirect('bus_list')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'users/verify_otp.html')
    return render(request, 'users/verify_otp.html')



def process_waitlist(bus):
    from .models import Waitlist
    available = unpack_available_seats_classes(bus.bus_number)
    waitlist_entries = Waitlist.objects.filter(bus=bus).order_by('created_at')
    
    for entry in waitlist_entries:
        for i in range(0,6):
            if entry.seats_requested <= list(available.values())[i]:
                send_mail(
                    f'Seats Available for Bus {bus.bus_number}',
                    f"Hello {entry.user.username}, seats are now available on bus {bus.bus_number}. Please visit our website to complete your booking.\nhttp://127.0.0.1:8000/book/{bus.bus_number}/",
                    settings.EMAIL_HOST_USER,
                    [entry.user.email],
                    fail_silently=False,
                )
                entry.delete()
                break
        else:
            continue