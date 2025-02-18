import pyotp
#from datetime import datetime, timedelta
from django.utils.timezone import make_aware
#from bus.models import Bus, BusInstance


def generate_otp():
    totp = pyotp.TOTP(pyotp.random_base32(), interval=300)  # 5 minutes validity
    return totp.now()

def verify_otp(otp, user_otp):
    return otp == user_otp


#############################################
'''def create_bus_instances_for_next_month(bus):
    today = datetime.now()
    end_date = today + timedelta(days=30)
    operating_days = bus.operating_days  
    current_date = today
    while current_date <= end_date:
        day_name = current_date.strftime('%A')  
        if day_name in operating_days:
            if not BusInstance.objects.filter(bus=bus, travel_date=current_date.date()).exists():
                BusInstance.objects.create(
                    bus=bus,
                    travel_date=current_date.date(),
                )
        current_date += timedelta(days=1)'''