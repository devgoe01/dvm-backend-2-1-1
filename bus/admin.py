from django.contrib import admin
from . import models

admin.site.register(models.User)
admin.site.register(models.Route)
admin.site.register(models.Bus)
admin.site.register(models.Booking)
admin.site.register(models.Seatclass)
admin.site.register(models.Waitlist)
#admin.site.register(models.Seat)