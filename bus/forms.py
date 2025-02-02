from django import forms
from . import models
from.utils import unpack_available_seats_classes
class BookingForm(forms.ModelForm):
    seats_booked=forms.IntegerField(required=True,label="Number of seats: ")
    seat_class=forms.CharField(required=True,label="Enter seat class general or luxury or sleeper: ")
    class Meta:
        model = models.Booking
        fields = ['seats_booked']
    def clean(self):
        cleaned_data = super().clean()
        seats_booked = cleaned_data.get('seats_booked')
        bus = self.instance.bus
        selected_class=cleaned_data.get('seat_class')
        if not(selected_class =="General" or selected_class =="Sleeper" or selected_class =="Luxury" or selected_class=="general" or selected_class=="sleeper" or selected_class=="luxury"):
            raise forms.ValidationError("Invalid seat class.")
        if seats_booked <= 0:
            raise forms.ValidationError("Number of seats must be greater than 0.")
        available_seats=int(unpack_available_seats_classes(bus.bus_number)[selected_class])
        if seats_booked > available_seats :
            raise forms.ValidationError(f"Only {bus.available_seats} seats are available.")
        return cleaned_data


class SearchForm(forms.Form):
    source = forms.CharField(max_length=20,required=True,label="Source")
    destination = forms.CharField(max_length=20,required=True,label="Destination")
    sort_by_departure = forms.BooleanField(required=False,label="check to sort by departure time else by available seats")


class EditBookingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.current_booking = kwargs.pop('current_booking', None)
        super().__init__(*args, **kwargs)

        if self.current_booking:
            self.fields['bus'].queryset = models.Bus.objects.filter(
                route=self.current_booking.bus.route,
                departure_time=self.current_booking.bus.departure_time
            )

    class Meta:
        model = models.Booking
        fields = ['bus', 'seats_booked', 'status']

    def cleaned_data(self):        
        seats_booked = super().cleaned_data('seats_booked')
        bus = super().cleaned_data('bus')

        if bus and seats_booked and (seats_booked is not None) and (seats_booked > bus.available_seats):
            raise forms.ValidationError(f"Only {bus.available_seats} seats are available on this bus.")

        return super().cleaned_data()
    

class EditBusForm(forms.ModelForm):
    class Meta:
        model = models.Bus
        fields = ['route', 'total_seats', 'departure_time', 'fare']