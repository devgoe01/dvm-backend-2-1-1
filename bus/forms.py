from django import forms
from . import models
from datetime import datetime

class BookingForm(forms.ModelForm):
    seats_booked = forms.IntegerField(required=True, label="Number of seats: ",help_text="Enter the number of seats you want to book.")
    seat_numbers = forms.CharField(max_length=100, required=False, label="Seat Number (optional): ")
    seat_class = forms.ModelChoiceField(queryset=models.BusSeatClass.objects.none(), required=True, label="Select seat class")
    start_stop = forms.ModelChoiceField(required=True, label="Select start stop",queryset=models.Stop.objects.none())
    end_stop = forms.ModelChoiceField(required=True, label="Select end stop",queryset=models.Stop.objects.none())
#    travel_date = forms.DateField(required=True, label="Travel Date")

    class Meta:
        model = models.Booking
        fields = ['start_stop','end_stop']

    def __init__(self, *args, **kwargs):
        bus = kwargs.pop('bus', None)
        super().__init__(*args, **kwargs)
        if bus and bus.route:
            self.fields['seat_class'].queryset = models.BusSeatClass.objects.filter(bus=bus)
            stop_choices = models.RouteStop.objects.filter(bus_route=bus.route).order_by('order')
            self.fields['start_stop'].queryset = stop_choices
            self.fields['end_stop'].queryset = stop_choices

    def clean(self):
        cleaned_data = super().clean()
        seats_booked = cleaned_data.get('seats_booked')
        start_stop = cleaned_data.get('start_stop')
        end_stop = cleaned_data.get('end_stop')
        if seats_booked <= 0:
            raise forms.ValidationError("Number of seats must be greater than 0.")
        if start_stop and end_stop:
            if start_stop.order >= end_stop.order:
                raise forms.ValidationError("Start stop must be before end stop.")
        return cleaned_data

class SearchForm(forms.Form):
    source = forms.ModelChoiceField(queryset=models.Stop.objects.all(),required=False, label="Source",empty_label="Select Source")
    destination = forms.ModelChoiceField(queryset=models.Stop.objects.all(),required=False, label="Destination",empty_label="Select Destination")

    sort_by_departure = forms.BooleanField(initial=True,required=False,label="Check to sort by departure time; otherwise by available seats")
    see_all_buses = forms.BooleanField(required=False,label="Check to see all buses")

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')

        if (not source or not destination) and not cleaned_data.get('see_all_buses'):
            raise forms.ValidationError("Please enter either source or destination.")
        
        return cleaned_data

class AddRouteForm(forms.ModelForm):
    stops_with_order = forms.CharField(
        required=True,
        label="Stops with Order",
        widget=forms.Textarea,
        help_text="Enter stops as a comma-separated list of 'stop:order' pairs (e.g., A:1, B:2, C:3)."
    )

    class Meta:
        model = models.BusRoute
        fields = ['name']

    def clean(self):
        cleaned_data = super().clean()
        stops_with_order = cleaned_data.get('stops_with_order')
        if not stops_with_order:
            raise forms.ValidationError("Stops with order is required.")
        try:
            stops_list = [
                tuple(item.strip().split(':')) for item in stops_with_order.split(',')
            ]
            stops_list = [(stop.strip(), int(order.strip())) for stop, order in stops_list]
        except ValueError:
            raise forms.ValidationError(
                "Invalid format. Use 'stop:order' pairs separated by commas (e.g., A:1, B:2)."
            )
        if len(stops_list) != len(set(stop[0] for stop in stops_list)):
            raise forms.ValidationError("Duplicate stop names are not allowed.")
        if len(stops_list) != len(set(stop[1] for stop in stops_list)):
            raise forms.ValidationError("Duplicate orders are not allowed.")
        if any(order <= 0 for _, order in stops_list):
            raise forms.ValidationError("Orders must be positive integers.")
        cleaned_data['stops_list'] = stops_list  
        return cleaned_data

class AddBusForm(forms.ModelForm):
    route = forms.ModelChoiceField(queryset=models.BusRoute.objects.all(),required=True,label="Route",help_text="Select an existing route for the bus.")
    departure_time = forms.DateTimeField(required=True,label="Departure Time",help_text="Enter in the format YYYY-MM-DD HH:MM:SS")
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour']

    def clean(self):
        cleaned_data = super().clean()
#        operating_days = cleaned_data.get('operating_days')
#        if not operating_days or not isinstance(operating_days, list):
#            raise forms.ValidationError("Operating days must be a list of valid days (e.g., ['Monday', 'Wednesday']).")
        return cleaned_data


class AddStopForm(forms.ModelForm):
    class Meta:
        model = models.Stop
        fields = ['name']
    def clean(self):
        return super().clean()

class SeatClassForm(forms.ModelForm):
    class Meta:
        model = models.BusSeatClass
        fields = ['seat_class', 'total_seats', 'fare_multiplier']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['seat_class'].queryset = models.Seatclass.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        total_seats = cleaned_data.get('total_seats')
        if total_seats <= 0:
            raise forms.ValidationError("Total seats must be greater than 0.")
        return cleaned_data


'''
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
'''


class EditBookingForm(forms.ModelForm):
    pass
class EditBusForm(forms.ModelForm):
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour']
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
    

class AddClassForm(forms.ModelForm):
    class Meta:
        model = models.Seatclass
        fields = ['name']