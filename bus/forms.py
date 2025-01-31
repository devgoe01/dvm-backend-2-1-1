from django import forms
from . import models
class BookingForm(forms.ModelForm):
    seats_booked=forms.IntegerField(required=True,label="Number of seats: ")
    class Meta:
        model = models.Booking
        fields = ['seats_booked']
    def clean_seats_booked(self):
        seats_booked = self.cleaned_data['seats_booked']
        bus = self.instance.bus
        
        if seats_booked <= 0:
            raise forms.ValidationError("Number of seats must be greater than 0.")
        if seats_booked > bus.available_seats :
            raise forms.ValidationError(f"Only {bus.available_seats} seats are available.")
        
        return seats_booked


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