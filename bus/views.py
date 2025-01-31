from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from .models import User,Route,Bus,Booking
from django.contrib import messages
from .forms import SearchForm,BookingForm,EditBookingForm,EditBusForm
from django.utils.timezone import now


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
        if form.is_valid():
            booking=form.save(commit=False)
            booking.user=request.user
            booking.bus=bus
            seats_booked=form.cleaned_data['seats_booked']
            if request.user.wallet_balance >= (seats_booked * bus.fare):
                request.user.wallet_balance -= (seats_booked * bus.fare)
                request.user.save()
                bus.available_seats -= seats_booked
                bus.save()
                booking.save()
                messages.success(request, "Your booking was successful!")
                return redirect('booking_summary')
            else:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('book_bus', bus_number=bus_number)
        else:
            messages.error(request, "Not enough seats available.")
                
    else:
        form=BookingForm()

    return render(request, 'bus/book_bus.html', {'form': form, 'bus': bus})

@login_required
def booking_summary(request):
    bookings=Booking.objects.filter(user=request.user)
    for booking in bookings:
        time_remaining=(booking.bus.departure_time - now()).total_seconds() /(60*60)
        booking.can_edit=time_remaining > 6
    print(bookings)
    return render(request, 'bus/booking_summary.html', {'bookings': bookings})


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
            if updated_booking.status == 'Cancelled':
                request.user.wallet_balance +=booking.seats_booked * booking.bus.fare
                request.user.save()
                booking.bus.available_seats += booking.seats_booked
                booking.bus.save()
            else:
                difference=updated_booking.seats_booked - original_seats_booked
                if difference > 0:
                    additional_cost=difference * booking.bus.fare
                    if request.user.wallet_balance >= additional_cost:
                        request.user.wallet_balance -= additional_cost
                        request.user.save()
                        booking.bus.available_seats -= difference
                        booking.bus.save()
                    else:
                        messages.error(request, "Insufficient wallet balance for additional seats.")
                        return redirect('edit_booking', booking_id=booking_id)
                elif difference < 0:
                    refund_amount=abs(difference) * booking.bus.fare
                    request.user.wallet_balance += refund_amount
                    request.user.save()
                    booking.bus.available_seats += abs(difference)
                    booking.bus.save()
                else:
                    messages.error(request, "No change in number of seats.")
                    return redirect('edit_booking', booking_id=booking_id)


            updated_booking.save()
            messages.success(request, "Booking updated successfully!")
            return redirect('booking_summary')
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