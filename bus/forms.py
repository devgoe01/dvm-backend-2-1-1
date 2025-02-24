from django import forms
from . import models
from datetime import datetime


class BookingForm(forms.ModelForm):
    seats_booked = forms.IntegerField(required=True, label="Number of seats: ")
    seat_number = forms.CharField(max_length=100, required=False, label="Seat Number (optional): ")
    seat_class = forms.ModelChoiceField(queryset=models.Seatclass.objects.all(), required=True, label="Select seat class")
    start_stop = forms.ChoiceField(required=True, label="Select start stop")
    end_stop = forms.ChoiceField(required=True, label="Select end stop")
#    travel_date = forms.DateField(required=True, label="Travel Date")

    class Meta:
        model = models.Booking
        fields = ['seats_booked', 'seat_class', 'seat_number']

    def __init__(self, *args, **kwargs):
        bus = kwargs.pop('bus', None)
        super().__init__(*args, **kwargs)
        self.fields['seat_class'].queryset = models.Seatclass.objects.filter(bus=bus)
        if bus and bus.route:
            ordered_stops = bus.route.get_ordered_stops()
            stop_choices = [(route_stop.stop.name, route_stop.stop.name) for route_stop in ordered_stops]
            self.fields['start_stop'].choices = stop_choices
            self.fields['end_stop'].choices = stop_choices

    def clean(self):
        cleaned_data = super().clean()
        seats_booked = cleaned_data.get('seats_booked')
        start_stop = cleaned_data.get('start_stop')
        end_stop = cleaned_data.get('end_stop')

        if seats_booked <= 0:
            raise forms.ValidationError("Number of seats must be greater than 0.")
        if start_stop and end_stop:
            bus_route = self.instance.bus.route
            ordered_stops = [route_stop.stop.name for route_stop in bus_route.get_ordered_stops()]
            if ordered_stops.index(start_stop) >= ordered_stops.index(end_stop):
                raise forms.ValidationError("End stop must come after start stop.")
        return cleaned_data


class SearchForm(forms.Form):
    source = forms.CharField(max_length=20, required=False, label="Source")
    destination = forms.CharField(max_length=20, required=False, label="Destination")
    sort_by_departure = forms.BooleanField(
        initial=True,
        required=False,
        label="Check to sort by departure time; otherwise by available seats"
    )
    see_all_buses = forms.BooleanField(
        required=False,
        label="Check to see all buses"
    )

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')

        if (not source or not destination) and not cleaned_data.get('see_all_buses'):
            raise forms.ValidationError("Please enter either source or destination.")
        
        return cleaned_data


class AddRouteForm(forms.ModelForm):
    stops_with_order = forms.JSONField(
        required=True,
        label="Stops with Order",
        help_text="Enter stops as a JSON array of objects with 'stop' and 'order' keys (e.g., [{'stop': 'A', 'order': 1}, {'stop': 'B', 'order': 2}])."
    )

    class Meta:
        model = models.BusRoute
        fields = ['name']
    def clean(self):
        cleaned_data = super().clean()
        stops_with_order = cleaned_data.get('stops_with_order')
        if not isinstance(stops_with_order, list) or not all(isinstance(item, dict) for item in stops_with_order):
            raise forms.ValidationError("Stops with order must be a list of dictionaries.")

        for item in stops_with_order:
            if 'stop' not in item or 'order' not in item:
                raise forms.ValidationError("Each dictionary must contain 'stop' and 'order' keys.")
            if not isinstance(item['order'], int) or item['order'] <= 0:
                raise forms.ValidationError("Order must be a positive integer.")

        return cleaned_data


class AddBusForm(forms.ModelForm):
    departure_time = forms.DateTimeField(
        required=True,
        label="Departure Time",
        help_text="Enter in the format YYYY-MM-DD HH:MM:SS"
    )
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour']
    def clean(self):
        cleaned_data = super().clean()
#        operating_days = cleaned_data.get('operating_days')
#        if not operating_days or not isinstance(operating_days, list):
#            raise forms.ValidationError("Operating days must be a list of valid days (e.g., ['Monday', 'Wednesday']).")
        return cleaned_data


class SeatClassForm(forms.ModelForm):
    seating_arrangement = forms.JSONField(
        required=False,
        label="Seating arrangement (JSON)",
        help_text="Enter seating arrangement as a JSON object (e.g., {'Seat-1': True, 'Seat-2': False})."
    )

    class Meta:
        model = models.Seatclass
        fields = ['name', 'total_seats', 'seats_available', 'fare_multiplier']

    def clean(self):
        cleaned_data = super().clean()
        total_seats = cleaned_data.get('total_seats')
        seats_available = cleaned_data.get('seats_available')
        if seats_available > total_seats:
            raise forms.ValidationError("Available seats cannot exceed total seats.")
        if total_seats <= 0:
            raise forms.ValidationError("Total seats must be greater than 0.")
        seating_arrangement = cleaned_data.get('seating_arrangement')
        if seating_arrangement and not isinstance(seating_arrangement, dict):
            raise forms.ValidationError("Seating arrangement must be a JSON object with seat numbers as keys.")
        return cleaned_data


class EditBookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.current_booking = kwargs.pop('current_booking', None)
        super().__init__(*args, **kwargs)
        if self.current_booking:
            self.fields['bus'].widget.attrs['readonly'] = True
            self.fields['seats_booked'].initial=self.current_booking.seats_booked
            self.fields['seat_class'].widget.attrs['readonly'] = True
    class Meta:
        model = models.Booking
        fields = ['bus', 'seats_booked', 'status', 'seat_class']

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

class EditBusForm(forms.ModelForm):
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour']
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data