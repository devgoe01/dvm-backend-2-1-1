from django.db import models,transaction
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta, datetime, timezone
from django.utils.timezone import make_aware
#from fernet_fields import EncryptedIntegerField
from multiselectfield import MultiSelectField
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class User(AbstractUser):
    ROLE_CHOICES = (('passenger', 'Passenger'), ('admin', 'Administrator'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='passenger')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    can_change_buses = models.ManyToManyField('Bus', related_name='editable_by', blank=True)
    email = models.EmailField(unique=True)

    def is_passenger(self):
        return self.role == 'passenger'

    def is_admin(self):
        return self.role == 'admin'


class Stop(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class BusRoute(models.Model):
    name = models.CharField(max_length=100, unique=True)
    stops = models.ManyToManyField(Stop, through='RouteStop', related_name='bus_routes')

    def __str__(self):
        return self.name
    
    def get_ordered_stops(self):
        return self.routestop_set.order_by('order')
    
    def get_stops_names(self):
        return [route_stop.stop.name for route_stop in self.get_ordered_stops()]
    
    def get_total_route_duration(self):
        total_duration = timedelta()
        for route_stop in self.get_ordered_stops():
            if route_stop.duration_to_next_stop:
                total_duration += route_stop.duration_to_next_stop
        return total_duration


class RouteStop(models.Model):
    bus_route = models.ForeignKey(BusRoute, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()   
    duration_to_next_stop = models.DurationField(null=True, blank=True)

    class Meta:
        unique_together = ('bus_route', 'stop', 'order')
        ordering = ['bus_route', 'order']
    
    def __str__(self):
        return f"{self.bus_route.name} - {self.stop.name} (Order: {self.order})"
 

class Bus(models.Model):
    bus_number = models.AutoField(primary_key=True)
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name="buses")
    departure_time=models.DateTimeField()
    base_fare_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    seat_classes = models.ManyToManyField('Seatclass', through='BusSeatClass', related_name='buses')
    Days_of_week = (('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday'))
    days_of_week_running = MultiSelectField(choices=Days_of_week,default='Monday',max_length=150)


    def calculate_fare(self, start_stop, end_stop, seat_class_multiplier,num_seats):
        ordered_stops = self.route.get_ordered_stops()
        start_index = (start_stop.order)
        end_index = (end_stop.order)

        total_duration = timedelta()
        for i in range(start_index, end_index):
            total_duration += ordered_stops[i].duration_to_next_stop

        total_hours = total_duration.total_seconds() / 3600
        return round(total_hours *num_seats* float(self.base_fare_per_hour) * float(seat_class_multiplier), 2)

    def __str__(self):
        return f"Bus {self.bus_number} on Route {self.route.name}"

    def initialize_bus_instances(self):
        today=datetime.now().date()
        with transaction.atomic():
            for bus in Bus.objects.all():
                running_days=bus.days_of_week_running

                for i in range(15):
                    current_date=today+timedelta(days=i)
                    current_day_name = current_date.strftime('%A')
                    if current_day_name in running_days:
                        departure_datetime = make_aware(datetime.combine(current_date, bus.departure_time.time()))
                        if not BusInstance.objects.filter(bus=bus, departure_time=departure_datetime).exists():
                            BusInstance.objects.create(bus=bus, departure_time=departure_datetime)

    def last_initialize_bus_instances(self):
        today=datetime.now().date()
        with transaction.atomic():
            for bus in Bus.objects.all():
                running_days=bus.days_of_week_running
                current_date=today+timedelta(days=15)
                if current_date.strftime('%A') in running_days:
                    departure_datetime = make_aware(datetime.combine(current_date, bus.departure_time.time()))
                    if not BusInstance.objects.filter(bus=bus, departure_time=departure_datetime).exists():
                        BusInstance.objects.create(bus=bus, departure_time=departure_datetime)

    def initialize_seats(self):
        with transaction.atomic():
            for seat_class in BusSeatClass.objects.filter(bus=self):
                for i in range(1,seat_class.total_seats+1):
                    Seat.objects.get_or_create(bus=self, seat_number=f"{seat_class.seat_class.name[:1]}-{i}",seat_class=seat_class)

class Seatclass(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} "


class BusSeatClass(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat_class = models.ForeignKey(Seatclass, on_delete=models.CASCADE,related_name="bus_seat_classes")
    total_seats = models.PositiveIntegerField()
    fare_multiplier = models.DecimalField(max_digits=4, decimal_places=2,default=1.0)
    class Meta:
        unique_together = ("bus", "seat_class")

    def __str__(self):
        return f"{self.bus} - {self.seat_class.name} (Total Seats:{self.total_seats} ),(Fare Multiplier:{self.fare_multiplier})"


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    seat_class=models.ForeignKey(BusSeatClass,on_delete=models.CASCADE)
    class Meta:
        unique_together = ("bus", "seat_number")

    def __str__(self):
        return f"Seat {self.seat_number} {self.seat_class.seat_class.name} on Bus {self.bus.bus_number}"

    def get_seat_class(self):
        return self.seat_class.seat_class.name

    def is_booked(self, bus_instance,start_stop, end_stop):
        overlapping_bookings = Booking.objects.filter(
            seats=self,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            bus=bus_instance,
            status='Confirmed'
        )
        return overlapping_bookings.exists()

    @staticmethod
    def are_seats_booked(bus_instance, seat_numbers, start_stop, end_stop, seat_class=None):
        booked_seats_query = Booking.objects.filter(
            bus=bus_instance,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        )
        if seat_class:
            booked_seats_query = booked_seats_query.filter(seats__seat_class=seat_class) 
        booked_seat_numbers = booked_seats_query.values_list('seats__seat_number', flat=True)

#        booked_seats_query.filter(seat_number__in=[f"{seat_class.seat_class.name[:1]}-{num}" for num in seat_numbers])
        seat_numbers = [f"{seat_class.seat_class.name[:1]}-{num}" for num in seat_numbers]

        booked_seats_in_requested = set(seat_numbers).intersection(set(booked_seat_numbers))
        return bool(booked_seats_in_requested), list(booked_seats_in_requested)


class Booking(models.Model):
    # Foreign key is written in many side of the relationship
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey("BusInstance", on_delete=models.CASCADE, related_name="bookings")
    seats = models.ManyToManyField(Seat,blank=True)
    booking_time = models.DateTimeField(auto_now_add=True)
    start_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="booking_start")
    end_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="booking_end")
    status = models.CharField(
        max_length=20,
        choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
        default='Confirmed'
    )
    
    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"
    def get_booked_seats(self):
        return self.seats.all()
    
    def booking_calculate_fare(self):
        return self.bus.bus.calculate_fare(self.start_stop, self.end_stop, self.seats.first().seat_class.fare_multiplier,len(self.seats.all()))
    
    def generate_ticket_pdf(self):
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        route = []
        for stop in self.bus.bus.route.get_ordered_stops():
            if self.start_stop.order <= stop.order <= self.end_stop.order:
                route.append(stop.stop.name)
        route = " → ".join(route)
        p.drawString(100, 780, f"Booking ID: {self.pk}")
        p.drawString(100, 760, f"Username: {self.user.username}")
        p.drawString(100, 740, f"Start Stop: {route}")
        p.drawString(100, 720, f"Booking Date: {self.booking_time.strftime('%A, %B %d, %Y, %I:%M %p')}")
        p.drawString(100, 700, f"Departure Time: {self.bus.departure_time.strftime('%A, %B %d, %Y, %I:%M %p')}")
        p.drawString(100, 680, f"Seat Numbers: {', '.join([seat.seat_number for seat in self.seats.all()])}")
        p.drawString(100, 660, f"Fare: {self.booking_calculate_fare()}")
        p.save()
        buffer.seek(0)
        return buffer
    
    def get_duration(self):
        total_duration = timedelta()
        for route_stop in self.bus.bus.route.get_ordered_stops():
            if self.start_stop.order <= route_stop.order <= self.end_stop.order:
                total_duration += route_stop.duration_to_next_stop
        return total_duration
    
    def display_ticket(self,response):
        p = canvas.Canvas(response, pagesize=letter)
        route = []
        for stop in self.bus.bus.route.get_ordered_stops(): 
            if self.start_stop.order <= stop.order <= self.end_stop.order:
                route.append(stop.stop.name)
        route = " → ".join(route)
        p.drawString(100, 780, f"Booking ID: {self.pk}")
        p.drawString(100, 760, f"Username: {self.user.username}")
        p.drawString(100, 740, f"Route: {route}")
        p.drawString(100, 720, f"Booking Date: {self.booking_time.strftime('%A, %B %d, %Y, %I:%M %p')}")
        p.drawString(100, 700, f"Departure Time: {self.bus.departure_time.strftime('%A, %B %d, %Y, %I:%M %p')}")
        p.drawString(100, 680, f"Seat Numbers: {', '.join([seat.seat_number for seat in self.seats.all()])}")
        p.drawString(100, 660, f"Fare: {self.booking_calculate_fare()}")
        p.showPage()
        p.save()
        return response

class Waitlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey("BusInstance", on_delete=models.CASCADE)
    seat_class = models.ForeignKey(BusSeatClass, on_delete=models.CASCADE)
    seats_requested = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Fulfilled', 'Fulfilled')],
        default='Pending'
    )
    start_stop=models.ForeignKey(RouteStop,on_delete=models.CASCADE,related_name="waitlist_start")
    end_stop=models.ForeignKey(RouteStop,on_delete=models.CASCADE,related_name="waitlist_end")

    def __str__(self):
        return f"Waitlist Entry: {self.user.username} for Bus {self.bus.bus.bus_number} class {self.seat_class.name}"


class Otps(models.Model):
    otp_code = models.PositiveIntegerField()
#    otp_code = models.EncyptedIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    otp_resend_attempts = models.PositiveIntegerField(default=0)
    max_resend_attempts = 5
    email=models.EmailField()
    is_verified=models.BooleanField(default=False)

    def save(self, *args, **kwargs):
#        if not self.expires_at:
        self.expires_at = datetime.now() + timedelta(minutes=2)
        self.created_at = datetime.now().isoformat()
        super().save(*args, **kwargs)

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    def can_resend(self):
        return self.otp_resend_attempts < self.max_resend_attempts

    def resend_otp(self,otp_code):
        self.otp_code = otp_code
        self.otp_resend_attempts += 1
        self.save()

    def __str__(self):
        return f"OTP for {self.email} created at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class BusInstance(models.Model):
    bus=models.ForeignKey(Bus,on_delete=models.CASCADE,related_name="bus_instances")
    departure_time=models.DateTimeField()

    def __str__(self):
        return f"Bus {self.bus.bus_number} Instance at {self.departure_time}"
    
    def is_departed(self):
        #print(f"\n\n\n\n{datetime.now(timezone.utc) > self.departure_time}\n\n\n\n")
        return datetime.now(timezone.utc) > self.departure_time

    def get_all_available_seats(self, start_stop, end_stop,seat_class=None):
        all_seats = self.seats.values_list('id', flat=True)
        booked_seats = Booking.objects.filter(
            bus=self,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        ).values_list('seats__id', flat=True)
        available_seats_ids = set(all_seats) - set(booked_seats)
        if seat_class:
            return self.seats.filter(id__in=available_seats_ids, seat_class=seat_class)
        return self.seats.filter(id__in=available_seats_ids)

   

    def are_seats_available(self,num_seats,start_stop,end_stop,seat_class):
        all_seats_in_class=self.bus.seats.filter(seat_class=seat_class).values_list('id',flat=True)
        booked_seats = Booking.objects.filter(
            bus=self,
            seats__seat_class=seat_class,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        ).values_list('seats__id', flat=True)
        available_seats = set(all_seats_in_class) - set(booked_seats)
        return len(available_seats) >= num_seats