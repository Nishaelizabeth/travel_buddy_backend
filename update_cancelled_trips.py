import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_buddy_backend.settings')
django.setup()

from auth_app.models import Trip
from django.utils import timezone

def update_cancelled_trips():
    # Get all trips with status 'cancelled'
    cancelled_trips = Trip.objects.filter(status='cancelled')
    print(f"Found {cancelled_trips.count()} cancelled trips to update")
    
    # Update each trip to set is_cancelled=True
    for trip in cancelled_trips:
        print(f"Updating trip ID {trip.id} to set is_cancelled=True")
        trip.is_cancelled = True
        
        # Ensure cancelled_at is set if it's not already
        if not trip.cancelled_at:
            trip.cancelled_at = timezone.now()
            
        # Save the trip with the updated fields
        trip.save(update_fields=['is_cancelled', 'cancelled_at'])
    
    print("Update completed successfully")

if __name__ == "__main__":
    update_cancelled_trips()
