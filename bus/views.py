import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import User, Bus, Booking, Seatclass,Waitlist,Otps,Seat,RouteStop,Stop,BusRoute,BusInstance
from django.contrib import messages
from .forms import AddSeatClassForm, SearchForm, BookingForm,AddRouteForm, EditBookingForm, EditBusForm, AddBusForm,SeatClassForm,AddStopForm,AddClassForm
from django.utils.timezone import now
from django.db.models import Sum, Prefetch
from django.core.mail import send_mail,EmailMessage
from django.db import transaction
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
    initializer()
    if request.user.role.lower() == 'admin':
        return render(request, 'bus/admin_dashboard.html')
    else:
        return render(request, 'bus/passenger_dashboard.html')



def search_func(travel_date,valid_routes,sort_by_departure):
    if travel_date:
        day_of_week = travel_date.strftime("%A")
        bus_instances=BusInstance.objects.filter(departure_time__date=travel_date,bus__days_of_week_running__contains=day_of_week)
        bus_instances = bus_instances.filter(bus__route__in=valid_routes).annotate(total_seats_available=Sum('bus__busseatclass__total_seats')).order_by('departure_time' if sort_by_departure else '-total_seats_available')
        #print(f"\n\n\n\n\n\n\n\n{bus_instances}\n\n\n\n\n\n\n\n")
        return None,bus_instances
    else:
        buses = Bus.objects.filter(route__in=valid_routes).annotate(total_seats_available=Sum('busseatclass__total_seats')).order_by('departure_time' if sort_by_departure else '-total_seats_available')
        #print(f"\n\n\n\n\n\n\n\n{buses}\n\n\n\n\n\n\n\n")
        return buses,None


def home(request):
    initializer()
    #buses = Bus.objects.select_related('route').prefetch_related('route__stops', 'seat_classes')
    bus_instances=None
    buses=None
    
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            source = form.cleaned_data.get('source',None)
            destination = form.cleaned_data.get('destination',None)
            sort_by_departure = form.cleaned_data['sort_by_departure']
            travel_date = form.cleaned_data.get('travel_date', None)
            if form.cleaned_data['see_all_buses']:
                buses=Bus.objects.select_related('route').prefetch_related('route__stops', 'seat_classes')
                bus_instances=None

                try :del request.session['search_data']
                except:pass
                request.session['search_data'] = json.dumps({ })
                return render(request, 'bus/home.html', {'form': form, 'buses': buses,'bus_instances':bus_instances})


            if source and not destination:
                valid_routes=[]
                source_stops=RouteStop.objects.filter(stop=source)
                #print(f"\n\n\n\n\n\n\n\n{source_stops}\n\n\n\n\n\n\n\n")
                for source_stop in source_stops:
                    if source_stop.order==source_stop.bus_route.routestop_set.last().order:
                        continue
                    valid_routes.append(source_stop.bus_route)
                #print(f"\n\n\n\n\n\n\n\n{valid_routes}\n\n\n\n\n\n\n\n")
                
                buses, bus_instances = search_func(travel_date,valid_routes,sort_by_departure)
                try :del request.session['search_data']
                except:pass
                request.session['search_data'] = json.dumps({
                    'source': source.id if source else None,
                    'destination': destination.id if destination else None,
                    'travel_date': str(travel_date) if travel_date else None
                })
                return render(request, 'bus/home.html', {'form': form, 'buses': buses,'bus_instances':bus_instances})
            

            if not source and destination:
                valid_routes=[]
                destination_stops=RouteStop.objects.filter(stop=destination)
                for destination_stop in destination_stops:
                    if destination_stop.order==destination_stop.bus_route.routestop_set.first().order:
                        continue
                    valid_routes.append(destination_stop.bus_route)
                
                buses, bus_instances = search_func(travel_date,valid_routes,sort_by_departure)
                try :del request.session['search_data']
                except:pass
                request.session['search_data'] = json.dumps({
                    'source': source.id if source else None,
                    'destination': destination.id if destination else None,
                    'travel_date': str(travel_date) if travel_date else None
                })
                return render(request, 'bus/home.html', {'form': form, 'buses': buses,'bus_instances':bus_instances})

            source_stops = RouteStop.objects.filter(stop=source)
            destination_stops = RouteStop.objects.filter(stop=destination)
            valid_routes = []
            for source_stop in source_stops:
                destination_stop = destination_stops.filter(
                    bus_route=source_stop.bus_route, 
                    order__gt=source_stop.order
                    ).first()
                if destination_stop:
                    valid_routes.append(source_stop.bus_route)
            

            if travel_date and not source:
                bus_instances=BusInstance.objects.filter(departure_time__date=travel_date).annotate(total_seats_available=Sum('bus__busseatclass__total_seats')).order_by('departure_time' if sort_by_departure else '-total_seats_available')
                try :del request.session['search_data']
                except:pass
                request.session['search_data'] = json.dumps({
                    'source': source.id if source else None,
                    'destination': destination.id if destination else None,
                    'travel_date': str(travel_date) if travel_date else None
                })
                return render(request, 'bus/home.html', {'form': form, 'buses': buses,'bus_instances':bus_instances})
            if not travel_date :
                buses = Bus.objects.filter(route__in=valid_routes).annotate(total_seats_available=Sum('busseatclass__total_seats')).order_by('departure_time' if sort_by_departure else '-total_seats_available')
            else:
                day_of_week = travel_date.strftime("%A")
                bus_instances=BusInstance.objects.filter(departure_time__date=travel_date,bus__days_of_week_running__contains=day_of_week)
                bus_instances = bus_instances.filter(bus__route__in=valid_routes).annotate(total_seats_available=Sum('bus__busseatclass__total_seats')).order_by('departure_time' if sort_by_departure else '-total_seats_available')
            
            try :del request.session['search_data']
            except:pass
            request.session['search_data'] = json.dumps({
                'source': source.id if source else None,
                'destination': destination.id if destination else None,
                'travel_date': str(travel_date) if travel_date else None
            })
    else:
        form = SearchForm()
    return render(request, 'bus/home.html', {'form': form, 'buses': buses,'bus_instances':bus_instances})



@login_required
def book_bus(request, bus_number):
    bus = get_object_or_404(Bus, bus_number=bus_number)
    if request.method == "POST":
        form=BookingForm(request.POST,bus=bus)
        form.instance.bus = bus.bus_instances.first()
        user = request.user

        if form.is_valid():
            user=request.user
            selected_class = form.cleaned_data['seat_class']
            seats_booked = form.cleaned_data['seats_booked']
            start_stop=form.cleaned_data['start_stop']
            end_stop=form.cleaned_data['end_stop']
            seat_numbers_input = form.cleaned_data.get('seat_numbers',None)
            travel_data = form.cleaned_data.get('travel_date')
            days_of_week = travel_data.strftime("%A")
            
            ''' stops=[bus.route.source]+bus.route.intermediate_stops+[bus.route.destination]'''
            ''' if start_stop not in stops or end_stop not in stops:
                messages.error(request, "Invalid start stop or end stop")
                return redirect('book_bus', bus_number=bus_number)
            if stops.index(start_stop) >= stops.index(end_stop):
                messages.error(request, "Start stop must be before end stop")
                return redirect('book_bus', bus_number=bus_number)'''
            bus=BusInstance.objects.get(departure_time__date=travel_data,bus=bus)
            booking=Booking(user=user,bus=bus,start_stop=start_stop,end_stop=end_stop)
            if not bus.are_seats_available(seats_booked,start_stop,end_stop,selected_class):
                messages.error(request, "Seats are not available")
                return redirect('book_bus', bus_number=bus_number)
        
            if seat_numbers_input:
                seat_numbers_list = [s.strip() for s in seat_numbers_input.split(',')]
                if len(seat_numbers_list) != seats_booked:
                    messages.error(request, "Number of seats booked does not match the entered seat numbers.")
                    return redirect('book_bus', bus_number=bus_number)
                are_booked,unavailable_seats=Seat.are_seats_booked(bus, seat_numbers_list, start_stop, end_stop, selected_class)
                if are_booked:
                    messages.error(request, f"The following seats are not available: {', '.join(unavailable_seats)}")
                    return redirect('book_bus', bus_number=bus_number)
##############
##############
##############
##############
##############
##############
##############
##############
            '''if seats_booked > selected_class.seats_available:
                waitlist=Waitlist.objects.create(user=user,bus=bus,seats_requested=seats_booked,seat_class=selected_class,status="Pending")
                waitlist.save()
                messages.info(request,"Seats are not available.You are in the waitlist .We will email you once seats are available.")
                return redirect('dashboard')'''
            

            total_cost=(bus.bus.calculate_fare(start_stop,end_stop,selected_class.fare_multiplier,seats_booked))

            if user.wallet_balance >= Decimal(total_cost):
                try:
                    if Otps.objects.get(email=request.user.email).exists():
                        otp_field= Otps.objects.filter(email=request.user.email).order_by('-created_at').first()
                        if ((otp_field.created_at - now().isoformat()).total_seconds() <240) and otp_field.is_verified==False and otp_field.otp_resend_attempts in [1,2]:
                            resend_attempts=otp_field.otp_resend_attempts
                        if ((otp_field.created_at - now().isoformat()).total_seconds() <600) and otp_field.is_verified==False and otp_field.otp_resend_attempts in [3,4,5]:
                            messages.error(request, "Wait for some time before requesting an otp again.")
                            return redirect('dashboard')
                except: pass    
                try : resend_attempts 
                except: resend_attempts=0
                email_otp = utils.generate_otp()
                otp=Otps.objects.create(otp_code=email_otp,email=request.user.email,otp_resend_attempts=resend_attempts)
                


                booked_seats = Booking.objects.filter(
                    bus=bus,
                    start_stop__order__lt=end_stop.order,
                    end_stop__order__gt=start_stop.order,
                    status='Confirmed'
                ).values_list('seats__id', flat=True)
                all_available_seats =bus.bus.seats.exclude(id__in=booked_seats).filter(seat_class=selected_class)


                if seat_numbers_input:
                    selected_seats = all_available_seats.filter(seat_number__in=[f"{selected_class.seat_class.name[:1]}-{num}" for num in seat_numbers_list])
                else:
                    selected_seats = list(all_available_seats)[:seats_booked]
                '''print(f"\n\n\n\n\n\n\n\n{all_available_seats}\n\n\n\n\n\n\n\n")
                print(f"\n\n\n\n\n\n\n\n{selected_seats}\n\n\n\n\n\n\n\n")
                print(f"\n\n\n\n\n\n\n\n{booked_seats}\n\n\n\n\n\n\n\n")
                print(f"\n\n\n\n\n\n\n\n{seat_numbers_input}\n\n\n\n\n\n\n\n")'''
                request.session['temp_booking'] = {
                    'otp_pk':otp.pk,
                    'bus_number': booking.bus.id,
                    'seats_booked': seats_booked,
                    'otp': email_otp,
                    'start_stop': start_stop.stop.id,
                    'end_stop': end_stop.stop.id,
                    'total_cost':total_cost,
                    'seat_numbers_list':[seat.id for seat in selected_seats],
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
        travel_date_from_session= None
        search_data = json.loads(request.session.get('search_data', {}))
        if search_data.get('travel_date',None):
            travel_date_from_session= datetime.strptime(search_data.get('travel_date'),'%Y-%m-%d').date()
        start_stop_from_session= search_data.get('source',None)
        end_stop_from_session= search_data.get('destination',None)
        form = BookingForm(bus=bus, travel_date_from_session=travel_date_from_session, start_stop_from_session=start_stop_from_session, end_stop_from_session=end_stop_from_session)

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
    last_resend_time = otp.created_at
    stored_otp = otp.otp_code
    otp_creation_time = now()
    bus=BusInstance.objects.get(id=temp_booking['bus_number'])
    start_stop = Stop.objects.get(id=temp_booking['start_stop'])
    end_stop = Stop.objects.get(id=temp_booking['end_stop'])
    start_stop = Stop.objects.get(id=temp_booking['start_stop'])
    start_stop = RouteStop.objects.get(bus_route=bus.bus.route, stop=start_stop)
    end_stop = RouteStop.objects.get(bus_route=bus.bus.route, stop=end_stop)
    seat_numbers_list = temp_booking['seat_numbers_list']
    seat_numbers_list = Seat.objects.filter(id__in=seat_numbers_list)
    if request.method == "POST":
        entered_otp = request.POST.get('email_otp')
        if entered_otp.lower()=='resend':

            cooldown_period = timedelta(seconds=30)
            if (now() - last_resend_time) < cooldown_period:
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
        if (utils.verify_otp(otp.otp_code, stored_otp)):
            if otp.is_expired():
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('verif_bus_otp')
            user = request.user
            bus_number = temp_booking['bus_number']
            seats_booked = temp_booking['seats_booked']
            start_stop=temp_booking['start_stop']
            end_stop=temp_booking['end_stop']
            start_stop = RouteStop.objects.filter(bus_route=bus.bus.route, stop__id=start_stop).first()
            end_stop = RouteStop.objects.filter(bus_route=bus.bus.route, stop__id=end_stop).first()
            total_cost=Decimal(temp_booking['total_cost'])
            otp.is_verified=True
#            travel_date=temp_booking['travel_date']
            '''print(bus_number, seats_booked, start_stop, end_stop,seat_numbers_list)'''
            if not all([bus_number, seats_booked, start_stop, end_stop,seat_numbers_list]):
                messages.error(request, "Session data is incomplete. Please try booking again.")
                return redirect('dashboard')
            bus=BusInstance.objects.get(id=bus_number)
            user.wallet_balance -= (total_cost)
           
            
            with transaction.atomic():
                otp.save()
                user.save()
                booking=Booking.objects.create(
                    user=user,
                    bus=bus,
                    status='Confirmed',
                    start_stop=start_stop,
                    end_stop=end_stop,
#                    travel_date=travel_date,
                )
                booking.seats.set(seat_numbers_list)
                messages.success(request, "Your booking was successful!")
            try :
                email=EmailMessage(
                    subject=f'Booking Confirmation for Bus {bus.bus.bus_number}',
                    body=f'Your booking for {seats_booked}.\n from {start_stop} to {end_stop} is successful.\nYour total cost is {total_cost:,.2f} rupees.\nYour booking id is {booking.id}.\n Departure time for bus is {bus.departure_time.strftime("%A, %B %d, %Y, %I:%M %p")}.',
                    from_email=settings.EMAIL_HOST_USER,
                    to=[request.user.email]
                )
                email.attach(f"ticket_{booking.id}.pdf", booking.generate_ticket_pdf().getvalue(), 'application/pdf')
                email.send(fail_silently=False)
            except: pass

            del request.session['temp_booking']
            return redirect('booking_summary')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    booking=Booking(user=request.user,bus=bus,start_stop=start_stop,end_stop=end_stop)
    return render(request, 'users/verify_otp.html', {'booking': booking,'seat_class':seat_numbers_list.first().seat_class.seat_class,'seat_numbers_list':seat_numbers_list,'fare':bus.bus.calculate_fare(start_stop,end_stop,seat_numbers_list.first().seat_class.fare_multiplier,seat_numbers_list.count())})

@login_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    time_remaining = (booking.bus.departure_time - now()).total_seconds() / 3600
    if time_remaining < 6 or booking.status == 'Cancelled':
        messages.error(request, "You cannot edit this booking.")
        return redirect('booking_summary')
#    original_seats_booked = booking.seats_booked
    if request.method == "POST":
        form = EditBookingForm(request.POST, instance=booking)
        if form.is_valid():
#            updated_booking = form.save(commit=False)
#            new_seats_booked = form.cleaned_data.get('seats_booked')
#            selected_class = form.cleaned_data.get('seat_class')
#            difference = new_seats_booked - original_seats_booked

#            if difference > selected_class.seats_available:
#                messages.error(request, f"Only {selected_class.seats_available} seats are available in {selected_class.name} class.")
#                return redirect('edit_booking', booking_id=booking_id)

            if form.cleaned_data.get('status') == 'Cancelled':# or new_seats_booked == 0:
#                x=original_seats_booked * Decimal(booking.bus.calculate_fare(selected_class.fare_multiplier,booking.start_stop,booking.end_stop))
#                request.user.wallet_balance += x
#                request.user.save()
#                updated_booking.save()
#                selected_class.save()
                request.user.wallet_balance += Decimal(booking.booking_calculate_fare())
                booking.status = 'Cancelled'
                with transaction.atomic():
                    request.user.save()
                    booking.save()
                try:
                    send_mail(
                        f'Booking cancelled for bus {booking.bus.bus.bus_number} on {booking.booking_time.strftime("%A, %B %d, %Y, %I:%M %p")}',
                        f'Booking for bus {booking.bus.bus.bus_number} has been cancelled.\n{booking.booking_calculate_fare():,.2f} rupees have been transferred to your wallet. Your updated balance is {request.user.wallet_balance:.2f} rupees.\n',
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=False)
                except:
                    pass
#                process_waitlist(booking.bus)
                return redirect('booking_summary')
            if form.cleaned_data.get('status') == 'Confirmed':
                messages.error(request, "No changes made.")
                return redirect('booking_summary')
            
            '''
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
                return redirect('edit_booking', booking_id=booking_id)'''
    else:
#        form=EditBookingForm(instance=booking, current_booking=booking)
        form=EditBookingForm(instance=booking)
    return render(request, 'bus/edit_booking.html', {'form': form, 'booking': booking})

@login_required
def booking_summary(request):
    bookings = Booking.objects.filter(user=request.user).select_related('bus', 'start_stop', 'end_stop').order_by('-booking_time')
    confirmed_bookings = bookings.filter(status='Confirmed').count()
    if not confirmed_bookings:
        confirmed_bookings = 'no'
    for booking in bookings:
        time_remaining = (booking.bus.departure_time - timezone.now()).total_seconds() / (60 * 60)
        booking.can_edit = time_remaining > 6 and (not booking.bus.is_departed()) and booking.status == 'Confirmed'
    context = {
        'bookings': bookings,
        'confirmed_bookings': confirmed_bookings,
    }
#    print(f"\n\n\n\n{context}\n\n\n\n")
    return render(request, 'bus/booking_summary.html', context)

@login_required
def admin_bus_list(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to view this page.")
        return redirect('dashboard')
    buses = request.user.can_change_buses.select_related('route').all()
    return render(request, 'bus/bus_list.html', {'buses': buses})

@login_required
def export_buses_to_excel(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to export data.")
        return redirect('dashboard')
    buses = request.user.can_change_buses.select_related('route').prefetch_related(
    Prefetch('bus_instances__bookings', queryset=Booking.objects.select_related('user', 'start_stop', 'end_stop'))
    ).prefetch_related('seat_classes').all()

    workbook = openpyxl.Workbook()
    sheet_buses = workbook.active
    sheet_buses.title = "Buses"
    headers_buses = ['Bus Number', 'Route Source', 'Route Destination', 'Departure Time', 'Total Seats', 'Base Fare Per Hour','Days of week running']
    sheet_buses.append(headers_buses)
    for bus in buses:
        total_seats = sum(cls.total_seats for cls in bus.busseatclass_set.all())
#        available_seats = sum(len(bus.get_all_available_seats(bus, None, cls)) for cls in bus.seat_classes.all())  

        row_buses = [
            bus.bus_number,
            bus.route.get_ordered_stops().first().stop.name if bus.route.get_ordered_stops().exists() else "N/A",
            bus.route.get_ordered_stops().last().stop.name if bus.route.get_ordered_stops().exists() else "N/A",
            bus.departure_time.strftime('%H:%M:%S'),
            total_seats,
#            available_seats,
            bus.base_fare_per_hour,
            ', '.join(bus.days_of_week_running) if bus.days_of_week_running else 'N/A',
        ]
        sheet_buses.append(row_buses)

    sheet_bookings = workbook.create_sheet(title="Bookings")
    headers_bookings = ['Booking ID', 'User', 'Bus Number', 'Departure Time','Seat Class', 'Seats Booked', 'Booking Time', 'Status']
    sheet_bookings.append(headers_bookings)
    bookings = Booking.objects.filter(bus__bus__in=buses).select_related('user', 'start_stop', 'end_stop')
    for booking in bookings:
        row_bookings = [
            booking.id,
            booking.user.username,
            booking.bus.bus.bus_number,
            booking.bus.departure_time.strftime('%A %Y-%m-%d %H:%M:%S'),
            booking.seats.first().seat_class.seat_class.name,
            booking.seats.count(),  
            booking.booking_time.strftime('%Y-%m-%d %H:%M:%S'),
            booking.status,
        ]
        sheet_bookings.append(row_bookings)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="buses_and_bookings.xlsx"'
    workbook.save(response)
    return response


@login_required
def add_route(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to add routes.")
        return redirect('dashboard')
    
    if request.method == "POST":
        route_form = AddRouteForm(request.POST)
        
        if route_form.is_valid():
            stops_list = route_form.cleaned_data['stops_list']
            duration_list = route_form.cleaned_data['duration_list']
            with transaction.atomic():
                route = route_form.save()
                for i, (stop_name, order) in enumerate(stops_list):
                    stop, _ = Stop.objects.get_or_create(name=stop_name)
                    RouteStop.objects.create(
                        bus_route=route,
                        stop=stop,
                        order=order,
                        duration_to_next_stop=duration_list[i]  
                    )
            messages.success(request, "Route added successfully!")
            return redirect('add_bus')  
        else:
            messages.error(request, "Please correct the errors in the form.")
    
    else:
        route_form = AddRouteForm()
    
    return render(request, 'bus/add_route.html', {'route_form': route_form})


@login_required
def add_stop(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to add stops.")
        return redirect('dashboard')
    if request.method == "POST":
        stop_form = AddStopForm(request.POST)
        if stop_form.is_valid():
            stop_form.save()
            messages.success(request, "Stop added successfully!")
            return redirect('view_stops')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        stop_form = AddStopForm()
    return render(request, 'bus/add_stop.html', {'stop_form': stop_form})

@login_required
def view_stops(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to view stops.")
        return redirect('dashboard')
    stops = Stop.objects.all()
    return render(request, 'bus/view_stops.html', {'stops': stops})

@login_required
def add_seat_class(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to add seat classes.")
        return redirect('dashboard')
    if request.method == "POST":
        seat_class_form = AddSeatClassForm(request.POST)
        if seat_class_form.is_valid():
            seat_class_form.save()
            messages.success(request, "Seat class added successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        seat_class_form = AddSeatClassForm()
    return render(request, 'bus/add_seat_class.html', {'seat_class_form': seat_class_form})

@login_required
def add_bus(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to add buses.")
        return redirect('dashboard')
    if request.method == "POST":
        bus_form = AddBusForm(request.POST)
        seat_class_forms = [SeatClassForm(request.POST, prefix=f'seat_class_{i}') for i in range(1, 4)]
        if bus_form.is_valid() and all(form.is_valid() for form in seat_class_forms):
            with transaction.atomic():
                bus = bus_form.save()
                for form in seat_class_forms:
                    seat_class = form.save(commit=False)
                    seat_class.bus = bus
                    seat_class.save()
                bus.initialize_seats()
                bus.initialize_bus_instances()
                request.user.can_change_buses.add(bus)
            messages.success(request, "Bus added successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        bus_form = AddBusForm()
        seat_class_forms = [SeatClassForm(prefix=f'seat_class_{i}') for i in range(1, 4)]

    return render(request, 'bus/add_bus.html', {
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
#            if form.cleaned_data['base_fare_per_hour'] != bus.base_fare_per_hour:
#                for bus_instance in bus.bus_instances.all():
#                    for booking in bus_instance.bookings.all():
#                        send_mail(
#                            'Bus Update',
#                            f"Bus {bus.bus_number} has been updated. Please check your dashboard for more details.",
#                            settings.EMAIL_HOST_USER,
#                            [booking.user.email],
#                            fail_silently=False,
#                        )
#                        booking.user.wallet_balance += (Decimal(booking.booking_calculate_fare()) - Decimal(bus_instance.bus.calculate_fare(booking.start_stop,booking.end_stop,booking.seat_class.fare_multiplier,booking.seats.count())))
#                        booking.user.save()
            bus = form.save()
            bus.departure_time = bus.departure_time.replace(hour=form.cleaned_data['departure_time'].hour, minute=form.cleaned_data['departure_time'].minute)
#            print(f"\n\n\n\n{bus.departure_time}\n\n\n\n")
#            print(f"\n\n\n\n{form.fields['departure_time']}\n\n\n\n")
            with transaction.atomic():
                bus.save()
                for bus_instance in bus.bus_instances.all():
                    bus_instance.departure_time = bus_instance.departure_time.replace(hour=bus.departure_time.hour, minute=bus.departure_time.minute)
                    bus_instance.save()
                    for booking in bus_instance.bookings.all():
                        send_mail(
                            'Bus Update',
                            f"Bus {bus.bus_number} has been updated. Please check your dashboard for more details.",
                            settings.EMAIL_HOST_USER,
                            [booking.user.email],
                            fail_silently=False,
                        )
            messages.success(request, "Bus updated successfully!")
#            process_waitlist(bus)
            return redirect('dashboard')
    else:
        form = EditBusForm(bus=bus)
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
            with transaction.atomic():
                for busm in bus.bus_instances.all():
                    for booking in Booking.objects.filter(bus=busm):
                        if booking.status == 'Confirmed':
                            user = booking.user
                            user.wallet_balance += Decimal(booking.booking_calculate_fare())
                            user.save()
                            try:
                                send_mail(
                                    f'Booking Cancelled for Bus {bus.bus_number}',
                                    f"Dear {user.username},\nYour booking for Bus {bus.bus_number} has been cancelled as the bus is no longer operational.\nYour updated wallet balance is {user.wallet_balance:,.2f} rupees.\nWe apologize for any inconvenience caused.\n",
                                    settings.EMAIL_HOST_USER,[request.user.email],fail_silently=False,
                                )
                            except:
                                pass
                bus.bus_instances.all().delete()
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
    count = sum(bus_instance.bookings.count() for bus_instance in bus.bus_instances.all())
    return render(request, 'bus/bus_bookings.html', {'bus': bus,'count':count})



@login_required
def add_class(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to add classes.")
        return redirect('dashboard')
    if request.method == "POST":
        class_form = AddClassForm(request.POST)
        if class_form.is_valid():
            class_form.save()
            messages.success(request, "Class added successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        class_form = AddClassForm()
    return render(request, 'bus/add_class.html', {'class_form': class_form})

def view_routes(request):
    if not request.user.is_admin():
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')
    routes = BusRoute.objects.all()
    return render(request, 'bus/view_routes.html', {'routes': routes})

def initializer():
    with transaction.atomic():
        for bus in Bus.objects.all():
            bus.initialize_bus_instances()

@login_required
def display_ticket(request,booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if (not request.user.can_change_buses.filter(bus_number=booking.bus.bus.bus_number).exists()) and request.user != booking.user:
        messages.error(request, "Invalid request.")
        return redirect('dashboard')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_{booking_id}.pdf"'
    return booking.display_ticket(response)

#from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
#from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView
#from django.views.generic import View
#from django.shortcuts import redirect
#
#class CustomGoogleOAuth2CallbackView(OAuth2CallbackView):
#    def dispatch(self, request, *args, **kwargs):
#        response = super().dispatch(request, *args, **kwargs)
#        if request.user.is_authenticated:
#            return redirect('/dashboard/')
#        return response