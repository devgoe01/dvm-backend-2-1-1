from.models import Bus

'''
def unpack_seat_classes(bus_number):
    seat_classes = Bus.objects.get(bus_number=bus_number).seat_classes
    general, sleeper, luxury = map(int, seat_classes.split('-'))
    return {'General': general, 'Sleeper': sleeper, 'Luxury': luxury}
def pack_seat_classes(general, sleeper, luxury):
#    bus=Bus.objects.get(bus_number=bus_number)
#    bus.seat_classes=f"{general}-{sleeper}-{luxury}"
#    bus.save()
    return f"{general}-{sleeper}-{luxury}"
'''
'''def unpack_available_seats_classes(bus_number):
    available_seats = Bus.objects.get(bus_number=bus_number).available_seats
    general, sleeper, luxury = map(int, available_seats.split('-'))
    return {'General': general,'general':general,'sleeper':sleeper,'luxury':luxury, 'Sleeper': sleeper, 'Luxury': luxury}
def pack_available_seats_classes(class_,num,bus_number):
    available_seats=Bus.objects.get(bus_number=bus_number).available_seats
    general, sleeper, luxury = map(int, available_seats.split('-'))
    if class_ == 'General' or class_ == 'general':
        general=num
    elif class_ == 'Sleeper' or class_ == 'sleeper':
        sleeper=num
    elif class_ == 'Luxury' or class_ == 'luxury':
        luxury=num
    return f"{general}-{sleeper}-{luxury}"

def unpack_booked_seats_class(seats_booked):
    general, sleeper, luxury = map(int, seats_booked.split('-'))
    if general :
        return {'general': 'general',"General": "General", 'seats_booked': general}
    if sleeper :
        return {'sleeper': 'sleeper','Sleeper': 'Sleeper', 'seats_booked': sleeper}
    if luxury :
        return {'luxury': 'luxury','Luxury': 'Luxury', 'seats_booked': luxury}

def pack_booked_seats(class_,num):
    if class_ == 'General' or class_ == 'general':
        general=num
        sleeper=0
        luxury=0
    elif class_ == 'Sleeper' or class_ == 'sleeper':
        general=0
        sleeper=num 
        luxury=0
    elif class_ == 'Luxury' or class_ == 'luxury':
        general=0
        sleeper=0
        luxury=num
    return f"{general}-{sleeper}-{luxury}"'''