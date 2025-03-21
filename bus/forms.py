from django import forms
from . import models
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

class BookingForm(forms.ModelForm):
    seats_booked = forms.IntegerField(required=True, label="Number of seats: ",help_text="Enter the number of seats you want to book.")
    seat_numbers = forms.CharField(max_length=100, required=False, label="Seat Number (optional): ")
    seat_class = forms.ModelChoiceField(queryset=models.BusSeatClass.objects.none(), required=True, label="Select seat class")
    start_stop = forms.ModelChoiceField(required=True, label="Select start stop",queryset=models.Stop.objects.none())
    end_stop = forms.ModelChoiceField(required=True, label="Select end stop",queryset=models.Stop.objects.none())
    travel_date = forms.DateField(required=False, label="Travel Date",widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = models.Booking
        fields = ['start_stop','end_stop']

    def __init__(self, *args, **kwargs):
        bus = kwargs.pop('bus', None)
        travel_date_f_s = kwargs.pop('travel_date_from_session', None)
        start_stop_f_s = kwargs.pop('start_stop_from_session', None)
        end_stop_f_s = kwargs.pop('end_stop_from_session', None)
        super().__init__(*args, **kwargs)
        print(f"\n\n\n\n{start_stop_f_s}\n\n\n\n")
        print(f"\n\n\n\n{end_stop_f_s}\n\n\n\n")
        if bus and bus.route:
            self.fields['seat_class'].queryset = models.BusSeatClass.objects.filter(bus=bus)
            stop_choices = models.RouteStop.objects.filter(bus_route=bus.route).order_by('order')
            self.fields['start_stop'].queryset = stop_choices
            self.fields['end_stop'].queryset = stop_choices
        if travel_date_f_s:
            self.fields['travel_date'].initial = travel_date_f_s
        if start_stop_f_s:
            self.fields['start_stop'].initial = stop_choices.get(stop_id=start_stop_f_s)
            self.fields['end_stop'].initial = stop_choices.get(stop_id=end_stop_f_s)

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
        if travel_date := cleaned_data.get('travel_date'):
            if travel_date < datetime.now().date():
                raise forms.ValidationError("Travel date must be in the future.")
            day_of_week = travel_date.strftime('%A')
            if not (day_of_week in self.instance.bus.bus.days_of_week_running):
                raise forms.ValidationError("Bus does not run on the selected day.")
            if not models.BusInstance.objects.filter(departure_time__date=travel_date,bus=self.instance.bus.bus).exists():
                raise forms.ValidationError("You cannot book this bus on the selected date so early.")
        return cleaned_data

class SearchForm(forms.Form):
    source = forms.ModelChoiceField(queryset=models.Stop.objects.all(),required=False, label="Source",empty_label="Select Source")
    destination = forms.ModelChoiceField(queryset=models.Stop.objects.all(),required=False, label="Destination",empty_label="Select Destination")
    travel_date = forms.DateField(required=False, label="Travel Date",widget=forms.DateInput(attrs={'type': 'date'}))

    sort_by_departure = forms.BooleanField(initial=True,required=False,label="Check to sort by departure time; otherwise by available seats")
    see_all_buses = forms.BooleanField(required=False,label="Check to see all buses")

    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')
        travel_date = cleaned_data.get('travel_date',None)
        if travel_date:
            if travel_date < datetime.now().date():
                raise forms.ValidationError("Travel date must be in the future.")
            if not models.BusInstance.objects.filter(departure_time__date=travel_date).exists():
                raise forms.ValidationError("No buses available on the selected date.")
        if not ( source or destination or travel_date or self.cleaned_data['see_all_buses']):
            raise forms.ValidationError("Please enter either source or destination.")
        
        return cleaned_data
class AddRouteForm(forms.ModelForm):
    stops_with_order = forms.CharField(
        required=True,
        label="Stops with Order",
        widget=forms.Textarea,
        help_text="Enter stops as a comma-separated list of 'stop:order' pairs (e.g., A:1, B:2, C:3)."
    )
    durations = forms.CharField(
        required=True,
        label="Durations (in seconds)",
        widget=forms.Textarea,
        help_text="Enter durations as a comma-separated list of integers representing seconds (e.g., 3600, 1800, 2400)."
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
        durations = cleaned_data.get('durations')
        if not durations:
            raise forms.ValidationError("Durations are required.")
        
        try:
            duration_list = [int(duration.strip()) for duration in durations.split(',')]
        except ValueError:
            raise forms.ValidationError("Durations must be integers representing seconds (e.g., 3600, 1800).")
        if len(duration_list) != len(stops_list):
            raise forms.ValidationError("The number of durations must match the number of stops.")
        cleaned_data['stops_list'] = stops_list
        cleaned_data['duration_list'] = [timedelta(seconds=seconds) for seconds in duration_list]
        
        return cleaned_data

class AddBusForm(forms.ModelForm):
    route = forms.ModelChoiceField(queryset=models.BusRoute.objects.all(),required=True,label="Route",help_text="Select an existing route for the bus.")
    departure_time = forms.TimeField(required=True,label="Departure Time",help_text="Enter in the format HH:MM:SS",widget=forms.TimeInput(attrs={'type': 'time'}))
    days_of_week_running = forms.MultipleChoiceField(
        required=True,
        label="Days of Week Running",
        widget=forms.CheckboxSelectMultiple,
        choices=models.Bus.Days_of_week)
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour','days_of_week_running']

    def clean(self):
        cleaned_data = super().clean()
        departure_time = cleaned_data.get('departure_time')
        aware_datetime=make_aware(datetime.combine(datetime.now().date(),departure_time))
        cleaned_data['departure_time'] = aware_datetime
#        operating_days = cleaned_data.get('operating_days')
#        if not operating_days or not isinstance(operating_days, list):
#            raise forms.ValidationError("Operating days must be a list of valid days (e.g., ['Monday', 'Wednesday']).")
        return cleaned_data

class AddSeatClassForm(forms.ModelForm):
    name = forms.CharField(required=True, label="Name", help_text="Enter the name of the seat class.")
    class Meta:
        model = models.Seatclass
        fields = ['name']

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
    class Meta:
        model = models.Booking
        fields = ['status']
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