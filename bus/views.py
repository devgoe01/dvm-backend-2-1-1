from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import User, Bus, Booking, Seatclass,Waitlist,Otps
from django.contrib import messages
from .forms import SearchForm, BookingForm,AddRouteForm, EditBookingForm, EditBusForm, AddBusForm,SeatClassForm
from django.utils.timezone import now
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from users import utils
from django.utils import timezone
from datetime import timedelta
import openpyxl
from django.http import HttpResponse
from decimal import Decimal
from datetime import datetime
#from celery import shared_task

@login_required
def dashboard(request):
    if request.user.role.lower() == 'admin':
        return render(request, 'bus/admin_dashboard.html')
    else:
        return render(request, 'bus/passenger_dashboard.html')


def home(request):
    buses = Bus.objects.all()
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            source = form.cleaned_data['source']
            destination = form.cleaned_data['destination']
            sort_by_departure = form.cleaned_data['sort_by_departure']
#           travel_date_str = request.GET.get('travel_date')
            if form.cleaned_data['see_all_buses']:
                buses = Bus.objects.all().annotate(total_seats_available=Sum('seat_classes__total_seats'))
                form=SearchForm()
                buses=buses.order_by('departure_time' if sort_by_departure else '-total_seats_available')
                return render(request, 'bus/home.html', {'form': form, 'buses': buses})
            try:
#                travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
#                day_of_week = travel_date.strftime('%A')
                buses = Bus.objects.filter(
                    route__source__icontains=source ,
                    route__destination__icontains=destination,
#                    operating_days__contains=[day_of_week]
                ).annotate(total_seats_available=Sum('seat_classes__total_seats'))
                buses=buses.order_by('departure_time' if sort_by_departure else '-total_seats_available')
            except :
                pass
    else:
        form = SearchForm()
    return render(request, 'bus/home.html', {'form': form, 'buses': buses})


@login_required
def book_bus(request, bus_number):
    bus = get_object_or_404(Bus, bus_number=bus_number)
    if request.method == "POST":
        form = BookingForm(request.POST,bus=bus)
        form.instance.bus = bus
        user = request.user
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = user
            booking.bus = bus
            selected_class = form.cleaned_data['seat_class']
            seats_booked = form.cleaned_data['seats_booked']
            start_stop=form.cleaned_data['start_stop']
            end_stop=form.cleaned_data['end_stop']
            seat_numbers = form.cleaned_data['seat_number']
            stops=[bus.route.source]+bus.route.intermediate_stops+[bus.route.destination]
            if start_stop not in stops or end_stop not in stops:
                messages.error(request, "Invalid start stop or end stop")
                return redirect('book_bus', bus_number=bus_number)
            if stops.index(start_stop) >= stops.index(end_stop):
                messages.error(request, "Start stop must be before end stop")
                return redirect('book_bus', bus_number=bus_number)
            if seat_numbers:
                seat_numbers_list = [s.strip() for s in seat_numbers.split(',')]
                if len(seat_numbers_list) != seats_booked:
                    messages.error(request, "Number of seats booked does not match the entered seat numbers.")
                    return redirect('book_bus', bus_number=bus_number)
                unavailable_seats = []
                for seat in seat_numbers_list:
                    seat=f"Seat-{seat}"
                    if not selected_class.seating_arrangement.get(seat):
                        unavailable_seats.append(seat)
                        a=selected_class.seating_arrangement.get(seat)
                if unavailable_seats:
                    messages.error(request, f"The following seats are not available: {', '.join(unavailable_seats)}")
                    return redirect('book_bus', bus_number=bus_number)
            else:
                seat_numbers_list = []
            if seats_booked > selected_class.seats_available:
                waitlist=Waitlist.objects.create(user=user,bus=bus,seats_requested=seats_booked,seat_class=selected_class,status="Pending")
                waitlist.save()
                messages.info(request,"Seats are not available.You are in the waitlist .We will email you once seats are available.")
                return redirect('dashboard')
            total_cost=seats_booked*(bus.calculate_fare(selected_class.fare_multiplier,start_stop,end_stop))
            total_cost=round(total_cost,2)
            if user.wallet_balance >= total_cost and selected_class.seats_available >= seats_booked:


                if Otps.objects.get(email=request.user.email).exists():
                    otp_field= Otps.objects.filter(email=request.user.email).order_by('-created_at').first()
                    if ((otp_field.created_at - now().isoformat()).total_seconds() <240) and otp_field.is_verified==False and otp_field.otp_resend_attempts in [1,2]:
                        resend_attempts=otp_field.otp_resend_attempts
                    if ((otp_field.created_at - now().isoformat()).total_seconds() <600) and otp_field.is_verified==False and otp_field.otp_resend_attempts in [3,4,5]:
                        messages.error(request, "Wait for some time before requesting an otp again.")
                        return redirect('dashboard')

                if not resend_attempts:
                    resend_attempts=0
                email_otp = utils.generate_otp()
                
                otp=Otps.objects.create(otp_code=email_otp,email=request.user.email,otp_resend_attempts=resend_attempts)
                request.session['temp_booking'] = {
                    'otp_pk':otp.pk,
                    'bus_number': booking.bus.bus_number,
                    'seats_booked': seats_booked,
                    'otp': email_otp,
                    'start_stop':start_stop,
                    'end_stop':end_stop,
                    'total_cost':total_cost,
                    'seat_numbers': seat_numbers_list,
#                    'travel_date':booking.travel_date,
                }
                send_mail(
                    f'Email Verification OTP',
                    f'Your OTP for email verification is: {email_otp}',
                    settings.EMAIL_HOST_USER,
                    [request.user.email],
                    fail_silently=False,
                )
                return redirect('verif_bus_otp')
            else:
                messages.error(request, "Insufficient wallet balance or not enough seats available.")
        else:
            messages.error(request, "Invalid form submission.")
    else: 
        form = BookingForm(bus=bus)
    return render(request, 'bus/book_bus.html', {'form': form, 'bus': bus})

@login_required
def verif_bus_otp(request):
    temp_booking = request.session.get('temp_booking', {})
    otp_id = temp_booking.get('otp_pk')
    otp=Otps.objects.get(pk=otp_id)
    if not temp_booking:
        messages.error(request, "Please try again.")
        return redirect('dashboard')
    otp_resend_attempts = otp.otp_resend_attempts
    last_resend_time = timezone.datetime.fromisoformat(otp.created_at)
    stored_otp = otp.otp_code
    otp_creation_time = now()

    if request.method == "POST":
        entered_otp = request.POST.get('email_otp')
        if entered_otp.lower()=='resend':

            cooldown_period = timedelta(seconds=30)
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP. Try booking again after some time.")
                return redirect('verif_bus_otp')

            if not otp.can_resend():
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.")
                return redirect('verif_bus_otp')

            new_otp = utils.generate_otp()
            otp.resend_otp(new_otp)
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [request.user.email],
                fail_silently=False,
            )
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verif_bus_otp')
        if utils.verify_otp(otp.otp_code, stored_otp):
            if otp.is_expired():
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verif_bus_otp')
            user = request.user
            bus_number = temp_booking['bus_number']
            seats_booked = temp_booking['seats_booked']
            selected_class_id = temp_booking['selected_class']
            selected_class = Seatclass.objects.get(id=selected_class_id)
            start_stop=temp_booking['start_stop']
            end_stop=temp_booking['end_stop']
            total_cost=Decimal(temp_booking['total_cost'])
            seat_numbers_list = temp_booking['seat_numbers']
#            travel_date=temp_booking['travel_date']
            bus=Bus.objects.get(bus_number=bus_number)
            user.wallet_balance -= (total_cost)
            user.save()
            

            booking=Booking.objects.create(
                user=user,
                bus=bus,
                seat_class=selected_class,
                seats_booked=seats_booked,
                status='Confirmed',
                start_stop=start_stop,
                end_stop=end_stop,
                seat_number=', '.join(seat_numbers_list),
#                travel_date=travel_date,
            )
            messages.success(request, "Your booking was successful!")
            try:
                send_mail(
                    f'Booking Confirmation for Bus {bus_number}',
                    f'Your booking for {seats_booked} seats in {selected_class.name} class is confirmed.\n from {start_stop} to {end_stop}.\nYour total cost is {total_cost:,.2f} rupees.\nYour booking id is {booking.id}.\n Departure time for bus is {bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
                    settings.EMAIL_HOST_USER,
                    [request.user.email],
                    fail_silently=False,
                )
            except: pass
            del request.session['temp_booking']
            return redirect('booking_summary')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    
    return render(request, 'users/verify_otp.html')


@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    time_remaining = (booking.bus.departure_time - now()).total_seconds() / 3600
    if time_remaining < 6 or booking.status == 'Cancelled':
        messages.error(request, "You cannot edit this booking.")
        return redirect('booking_summary')
    original_seats_booked = booking.seats_booked
    if request.method == "POST":
        form = EditBookingForm(request.POST, instance=booking)
        if form.is_valid():
            updated_booking = form.save(commit=False)
            new_seats_booked = form.cleaned_data.get('seats_booked')
            selected_class = form.cleaned_data.get('seat_class')
            difference = new_seats_booked - original_seats_booked

            if difference > selected_class.seats_available:
                messages.error(request, f"Only {selected_class.seats_available} seats are available in {selected_class.name} class.")
                return redirect('edit_booking', booking_id=booking_id)

            if updated_booking.status == 'Cancelled' or new_seats_booked == 0:
                x=original_seats_booked * Decimal(booking.bus.calculate_fare(selected_class.fare_multiplier,booking.start_stop,booking.end_stop))
                request.user.wallet_balance += x
                request.user.save()
                updated_booking.save()
                selected_class.save()
                try:
                    send_mail(
                        f'Booking cancelled for bus {booking.bus.bus_number} on {booking.booking_time.strftime("%A, %B %d, %Y, %I:%M %p")}',
                        f'Booking for bus {booking.bus.bus_number} has been cancelled.\n{x} rupees have been transferred to your wallet. Your updated balance is {request.user.wallet_balance:.2f} rupees.\n',
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False)
                except:
                    pass
                process_waitlist(booking.bus)
                return redirect('booking_summary')

            if difference != 0 and updated_booking.status == 'Confirmed':
                if difference > 0:
                    additional_cost = difference * Decimal(booking.bus.calculate_fare(selected_class.fare_multiplier,booking.start_stop,booking.end_stop))
                    if request.user.wallet_balance >= additional_cost:
                        request.user.wallet_balance -= additional_cost
                        request.user.save()
                        updated_booking.assign_additional_seats(difference)
                        updated_booking.save()
                        messages.success(request, "Booking updated successfully!")
                    else:
                        messages.error(request, "Insufficient wallet balance.")
                        return redirect('edit_booking', booking_id=booking_id)
                elif difference < 0:
                    refund_amount = abs(difference) * Decimal(booking.bus.calculate_fare(selected_class.fare_multiplier,booking.start_stop,booking.end_stop))
                    request.user.wallet_balance += refund_amount
                    request.user.save()
                    updated_booking.release_seats(booking)
                    updated_booking.save()
                    process_waitlist(booking.bus)
                    messages.success(request, "Booking updated successfully!")
                try:
                    send_mail(
                        f'Updated booking status for bus {booking.bus.bus_number} on {booking.bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}',
                        f'Booking status for bus {booking.bus.bus_number} has been updated.\n{new_seats_booked} seats are booked for bus {booking.bus.bus_number} from {booking.bus.route.source} to {booking.bus.route.destination}.\nYour current wallet balance is {request.user.wallet_balance:.2f} rupees.',
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False)
                except:
                    pass
                
            elif difference == 0:
                messages.error(request, "No changes made to booking.")
                return redirect('edit_booking', booking_id=booking_id)
    else:
        form=EditBookingForm(instance=booking, current_booking=booking)
    return render(request, 'bus/edit_booking.html', {'form': form, 'booking': booking})

@login_required
def booking_summary(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_time')
    confirmed_bookings = bookings.filter(status='Confirmed').count()
    if not confirmed_bookings:
        confirmed_bookings = 'no'
    for booking in bookings:
        time_remaining = (booking.bus.departure_time - timezone.now()).total_seconds() / (60 * 60)
        booking.can_edit = time_remaining > 6

    context = {
        'bookings': bookings,
        'confirmed_bookings': confirmed_bookings,
    }
    return render(request, 'bus/booking_summary.html', context)


@login_required
def admin_bus_list(request):
    if request.user.role.lower() != 'admin':
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')

    buses = request.user.can_change_buses.all()
    return render(request, 'bus/bus_list.html', {'buses': buses})


@login_required
def export_buses_to_excel(request):
    if not request.user.is_authenticated or request.user.role.lower() == 'passenger':
        messages.error(request, "You do not have permission to export data.")
        return redirect('dashboard')

    buses = request.user.can_change_buses.all()
    
    workbook = openpyxl.Workbook()
    sheet_buses = workbook.active
    sheet_buses.title = "Buses"
    
    headers_buses = ['Bus Number', 'Route Source', 'Route Destination', 'Departure Time', 'Total Seats', 'Available Seats', 'Fare']
    sheet_buses.append(headers_buses)

    for bus in buses:
        row_buses = [
            bus.bus_number,
            bus.route.source,
            bus.route.destination,
            bus.departure_time.strftime('%Y-%m-%d %H:%M:%S'),
            sum(cls.total_seats for cls in bus.seat_classes.all()),
            sum(cls.seats_available for cls in bus.seat_classes.all()),
            bus.base_fare_per_hour,
        ]
        sheet_buses.append(row_buses)

    sheet_bookings = workbook.create_sheet(title="Bookings")
    headers_bookings = ['Booking ID', 'User', 'Bus Number', 'Seat Class', 'Seats Booked', 'Booking Time', 'Status']
    sheet_bookings.append(headers_bookings)
    bookings = Booking.objects.filter(bus__in=buses)
    for booking in bookings:
        row_bookings = [
            booking.id,
            booking.user.username,
            booking.bus.bus_number,
            booking.seat_class.name,
            booking.seats_booked,
            booking.booking_time.strftime('%Y-%m-%d %H:%M:%S'),
            booking.status,
        ]
        sheet_bookings.append(row_bookings)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="buses_and_bookings.xlsx"'
    workbook.save(response)
    return response

@login_required
def add_bus(request):
    if request.user.role.lower() != 'admin':
        messages.error(request, "You do not have permission to add buses.")
        return redirect('dashboard')
    if request.method == "POST":
        bus_form = AddBusForm(request.POST)
        route_form = AddRouteForm(request.POST)
        bus_form = AddBusForm(request.POST)
        seat_class_forms = [SeatClassForm(request.POST, prefix=f'seat_class_{i}') for i in range(1, 4)]
        if route_form.is_valid() and bus_form.is_valid() and all(form.is_valid() for form in seat_class_forms):
            route = route_form.save()
            bus = bus_form.save(commit=False)
            bus.route = route
            bus.save()
            for form in seat_class_forms:
                seating_arrangement={}
                seating_arrangement={f"Seat-{i+1}": True for i in range(form.cleaned_data['total_seats'])}
                seat_class = form.save(commit=False)
                seat_class.bus = bus
                seat_class.seating_arrangement=seating_arrangement
                seat_class.save()
            messages.success(request, "Bus and its route added successfully!")
            request.user.can_change_buses.add(bus)
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        route_form = AddRouteForm()
        bus_form = AddBusForm()
        seat_class_forms = [SeatClassForm(prefix=f'seat_class_{i}') for i in range(1, 4)]
    return render(request, 'bus/add_bus.html', {
        'route_form': route_form,
        'bus_form': bus_form,
        'seat_class_forms': seat_class_forms,
    })


def about(request):
    return render(request, 'bus/about.html', {'title': 'About'})

@login_required
def edit_bus(request, bus_number):
    bus = get_object_or_404(Bus, bus_number=bus_number)

    if not (request.user.role.lower() == 'admin' and request.user.can_change_buses.filter(bus_number=bus_number).exists()):
        messages.error(request, "You are not authorized to edit this bus.")
        return redirect('dashboard')
    if request.method == "POST":
        form = EditBusForm(request.POST, instance=bus)
        if form.is_valid():
            bus.save()
            messages.success(request, "Bus updated successfully!")
            process_waitlist(bus)
            return redirect('dashboard')
    else:
        form = EditBusForm(instance=bus)
    return render(request, 'bus/edit_bus.html', {'form': form})


@login_required
def delete_bus(request, bus_number):
    try:
        bus = Bus.objects.get(bus_number=bus_number)
    except Bus.DoesNotExist:
        messages.error(request, "Bus not found.")
        return redirect('dashboard')

    if request.user.role.lower() != 'admin' or bus not in request.user.can_change_buses.all():
        messages.error(request, "You do not have permission to delete this bus.")
        return redirect('dashboard')

    if request.method == "POST":
        email_otp = utils.generate_otp()
        request.session['temp_del'] = {
            'bus_number': bus_number,
            'otp': email_otp,
            'otp_creation_time': now().isoformat(),
            'otp_resend_attempts': 1,
        }
        send_mail(
            'OTP for verification',
            f'Your OTP is: {email_otp}',
            settings.EMAIL_HOST_USER,
            [request.user.email],
            fail_silently=False,
        )
        return redirect('verify_del_bus_otp')

    return render(request, 'bus/delete_bus.html', {'bus': bus})


@login_required
def verif_del_bus_otp(request):
    temp_del = request.session.get('temp_del')
    entered_otp = request.POST.get('email_otp')
    stored_otp = temp_del['otp']
    otp_resend_attempts = temp_del['otp_resend_attempts']
    otp_creation_time = now()

    if not temp_del:
        messages.error(request, "Please try again.")
        return redirect('dashboard')

    if request.method == "POST":
        if entered_otp.lower() == 'resend':
            cooldown_period = timedelta(seconds=30)
            last_resend_time = timezone.datetime.fromisoformat(temp_del['otp_creation_time'])
            
            if timezone.now() - last_resend_time < cooldown_period:
                messages.error(request, "Please wait before requesting another OTP.")
                return redirect('verify_del_bus_otp')

            max_resend_attempts = 5
            if otp_resend_attempts >= max_resend_attempts:
                messages.error(request, "You have exceeded the maximum number of OTP resend attempts.")
                return redirect('verify_del_bus_otp')

            new_otp = utils.generate_otp()
            temp_del['otp'] = new_otp
            temp_del['otp_creation_time'] = now().isoformat()
            
            send_mail(
                'New OTP for verification',
                f'Your new OTP is: {new_otp}',
                settings.EMAIL_HOST_USER,
                [request.user.email],
                fail_silently=False,
            )
            temp_del['otp_resend_attempts'] += 1
            request.session['temp_del'] = temp_del
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verify_del_bus_otp')
        elif utils.verify_otp(entered_otp, stored_otp):
            if (now() - timedelta(minutes=2)) > otp_creation_time:
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verify_del_bus_otp')
            bus_number = temp_del['bus_number']
            bus=Bus.objects.get(bus_number=bus_number)
            for booking in Booking.objects.filter(bus=bus):
                if booking.status == 'Confirmed':
                    user = booking.user
                    user.wallet_balance += booking.seats_booked * Decimal(bus.calculate_fare(booking.seat_class.fare_multiplier,booking.start_stop,booking.end_stop))
                    user.save()
                    try:
                        send_mail(
                            f'Booking Cancelled for Bus {bus.bus_number}',
                            f"Dear {user.username},\nYour booking for Bus {bus.bus_number} has been cancelled as the bus is no longer operational.\nYour updated wallet balance is {user.wallet_balance:,.2f} rupees.\nWe apologize for any inconvenience caused.\n",
                            settings.EMAIL_HOST_USER,[request.user.email],fail_silently=False,
                        )
                    except:
                        pass
            bus.route.delete()
            bus.delete()
            Bus.objects.filter(bus_number=bus_number).delete()
            del request.session['temp_del']
            messages.success(request, f"Bus {bus_number} deleted successfully!")
            return redirect('bus_list')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    return render(request, 'users/verify_otp.html')


#@shared_task
def process_waitlist(bus):
    waitlist_entries = Waitlist.objects.filter(bus=bus,status="Pending").order_by('created_at')
    for entry in waitlist_entries:
        seat_class=entry.seat_class
        if entry.seats_requested <= seat_class.seats_available:
            send_mail(
                f'Seats Available for Bus {bus.bus_number} class {seat_class.name}',
                f"Hello {entry.user.username}, seats are now available on bus {bus.bus_number} class {seat_class.name}. Please visit our website to complete your booking.\nhttp://127.0.0.1:8000/book/{bus.bus_number}/",
                settings.EMAIL_HOST_USER,
                [entry.user.email],
                fail_silently=False,
            )
            entry.status = "Fulfilled"
            entry.save()
            break
        else:
            continue

@login_required
def bus_bookings(request, bus_number):
    if request.user.role=="passenger":
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')
    bus = get_object_or_404(Bus, bus_number=bus_number)
    return render(request, 'bus/bus_bookings.html', {'bus': bus})