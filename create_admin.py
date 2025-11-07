import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_buddy_backend.settings')
django.setup()

# Import the UserProfile model
from auth_app.models import UserProfile

# Check if admin user exists
try:
    admin_user = UserProfile.objects.get(username='admin')
    print(f"Admin user found: {admin_user.username}")
    print(f"Is staff: {admin_user.is_staff}")
    print(f"Is superuser: {admin_user.is_superuser}")
    
    # If admin user exists but doesn't have admin privileges, update them
    if not (admin_user.is_staff or admin_user.is_superuser):
        print("Updating admin user with admin privileges...")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        print("Admin privileges granted.")
        
except UserProfile.DoesNotExist:
    print("Admin user not found. Creating admin user...")
    admin_user = UserProfile.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin',
        full_name='Admin User'
    )
    print(f"Admin user created with username: {admin_user.username}")
    print(f"Is staff: {admin_user.is_staff}")
    print(f"Is superuser: {admin_user.is_superuser}")