from django import forms
from . import models
from datetime import datetime

class BookingForm(forms.ModelForm):
    seats_booked = forms.IntegerField(required=True, label="Number of seats: ")
    seat_number= forms.CharField(max_length=100, required=False, label="Seat Number:(optional) ")
    seat_class = forms.ModelChoiceField(queryset=models.Seatclass.objects.all(),required=True,label="Select seat class")
    start_stop=forms.ChoiceField(required=True,label="Select start stop")
    end_stop=forms.ChoiceField(required=True,label="Select end stop")
#    travel_date = forms.DateField(required=True, label="Travel Date")
    class Meta:
        model = models.Booking
        fields = ['seats_booked', 'seat_class', 'seat_number']

    def __init__(self, *args, **kwargs):
        bus = kwargs.pop('bus', None)
        super().__init__(*args, **kwargs)
        self.fields['seat_class'].queryset = models.Seatclass.objects.filter(bus=bus)
        stops = [bus.route.source] + bus.route.intermediate_stops + [bus.route.destination]
        stop_choices = [(stop, stop) for stop in stops]
        self.fields['start_stop'].choices = stop_choices
        self.fields['end_stop'].choices = stop_choices
    def clean(self):
        cleaned_data = super().clean()
        seats_booked = cleaned_data.get('seats_booked')
        seat_class = cleaned_data.get('seat_class')
#        travel_date = cleaned_data.get('travel_date')
        '''
        try:
            bus_instance=models.BusInstance.objects.get(bus=seat_class.bus_instance.bus,travel_date=travel_date)
        except models.BusInstance.DoesNotExist: 
            raise forms.ValidationError(f"No bus instance found for {seat_class.bus_instance.bus.bus_number} on {travel_date}.")'''
        
#        if travel_date < datetime.now().date():
#            raise forms.ValidationError("Travel date cannot be in the past.")
        if not seat_class:
            raise forms.ValidationError("Please select a valid seat class.")
        if seats_booked <= 0:
            raise forms.ValidationError("Number of seats must be greater than 0.")

        return cleaned_data

class SearchForm(forms.Form):
    source = forms.CharField(max_length=20, required=False, label="Source")
    destination = forms.CharField(max_length=20, required=False, label="Destination")
    sort_by_departure = forms.BooleanField(initial=True,
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

class EditBookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.current_booking = kwargs.pop('current_booking', None)
        super().__init__(*args, **kwargs)

        if self.current_booking:
            self.fields['bus'].queryset = models.Bus.objects.filter(
                route=self.current_booking.bus.route,
                departure_time=self.current_booking.bus.departure_time
            )
            self.fields['bus'].widget.attrs['readonly'] = 'readonly'
            self.fields['seats_booked'].initial = self.current_booking.seats_booked
            self.fields['seat_class'].widget.attrs['readonly'] = 'readonly'
    class Meta:
        model = models.Booking
        fields = ['bus', 'seats_booked', 'status','seat_class']

    def clean(self):
        cleaned_data = super().clean()
        seats_booked = cleaned_data.get('seats_booked')
        bus = cleaned_data.get('bus')
        seat_class = cleaned_data.get('seat_class')

        if not bus or not seat_class:
            raise forms.ValidationError("Bus and seat class must be selected.")
        return cleaned_data

class AddRouteForm(forms.ModelForm):
    intermediate_stops=forms.JSONField(required=False,label="Intermediate Stops",help_text="Enter stops separated as a JSON array (eg ['Stop-1', 'Stop-2'])")
    stop_durations = forms.JSONField(required=True, label="Duration",help_text="Enter durations as a JSON object (e.g., {'City A-City B': 3600, 'City B-City C': 5400}).")
    class Meta:
        model = models.Route
        fields = ['source', 'destination','intermediate_stops','stop_durations']

    def clean(self):
        cleaned_data = super().clean()
        intermediate_stops = cleaned_data.get('intermediate_stops',[])
        if not intermediate_stops:
            intermediate_stops=[]
        stop_durations = cleaned_data.get('stop_durations',{})
        if intermediate_stops and not isinstance(intermediate_stops, list):
            raise forms.ValidationError("Intermediate stops must be a list.")
        stops=[cleaned_data['source']]+intermediate_stops+[cleaned_data['destination']]
        for i in range(len(stops)-1):
            key=f"{stops[i]}-{stops[i+1]}"
            if key not in stop_durations:
                raise forms.ValidationError(f"Duration for {key} is missing.")
        return cleaned_data

class AddBusForm(forms.ModelForm):
    departure_time = forms.DateTimeField(required=True, label="Departure Time",help_text="Enter in the format YYYY-MM-DD HH:MM:SS")
    class Meta:
        model = models.Bus
        fields = ['departure_time', 'base_fare_per_hour']
    def clean(self):
        cleaned_data = super().clean()
#        operating_days = cleaned_data.get('operating_days')
#        if not operating_days or not isinstance(operating_days, list):
#            raise forms.ValidationError("Operating days must be a list of valid days (e.g., ['Monday', 'Wednesday']).")
        return cleaned_data

class SeatClassForm(forms.ModelForm):
    seating_arrangement = forms.JSONField(required=False, label="Seating arrangement (JSON) eg {'Seat-1': True, 'Seat-2': False}")
    class Meta:
        model = models.Seatclass
        fields = ['name', 'total_seats', 'seats_available','fare_multiplier']

    def clean(self):
        cleaned_data = super().clean()
        total_seats = cleaned_data.get('total_seats')
        seats_available = cleaned_data.get('seats_available')
        seating_arrangement = cleaned_data.get('seating_arrangement')
        if seats_available>total_seats:
            raise forms.ValidationError("Available seats cannot exceed total seats.")
        if total_seats<=0:
            raise forms.ValidationError("Total seats must be greater than 0.")
        if seating_arrangement and not isinstance(seating_arrangement, dict):
            raise forms.ValidationError("Seating arrangement must be a JSON object with seat numbers as keys.")
        if cleaned_data['seats_available'] > cleaned_data['total_seats']:
            self.add_error('seats_available', "Available seats cannot exceed total seats.")
        return cleaned_data
    
class EditBusForm(forms.ModelForm):
    '''intermediate_stops=forms.JSONField(required=False,label="Intermediate Stops",help_text="Enter stops separated as a JSON array")'''
    class Meta:
        model = models.Bus
        fields = ['route', 'departure_time', 'base_fare_per_hour']

    def clean(self):
        cleaned_data = super().clean()
        '''intermediate_stops = cleaned_data.get('intermediate_stops')
        if intermediate_stops and not isinstance(intermediate_stops, list):
            raise forms.ValidationError("Intermediate stops must be a list.")'''
        return cleaned_data


'''
class EditSeatClassForm(forms.ModelForm):
    seating_arrangement = forms.JSONField(required=False, label="Seating arrangement (JSON) eg {'Seat-1': True, 'Seat-2': False}")
    class Meta:
        model = models.Seatclass
        fields = ['name', 'total_seats', 'seats_available','fare_multiplier']

    def clean(self):
        cleaned_data = super().clean()
        total_seats = cleaned_data.get('total_seats')
        seats_available = cleaned_data.get('seats_available')
        seating_arrangement = cleaned_data.get('seating_arrangement')
        if seats_available>total_seats:
            raise forms.ValidationError("Available seats cannot exceed total seats.")
        if seating_arrangement and not isinstance(seating_arrangement, dict):
            raise forms.ValidationError("Seating arrangement must be a JSON object with seat numbers as keys.")
        if cleaned_data['seats_available'] > cleaned_data['total_seats']:
            self.add_error('seats_available', "Available seats cannot exceed total seats.")
        return cleaned_data'''