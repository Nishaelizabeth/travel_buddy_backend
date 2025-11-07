# This script ensures a Django superuser is created on every deploy if it doesn't exist.
# Usage: Add this script to your backend and call it in your Render deploy/build/start command.

import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_buddy_backend.settings')
django.setup()

User = get_user_model()

ADMIN_USERNAME = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
ADMIN_EMAIL = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
ADMIN_PASSWORD = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')

if not User.objects.filter(username=ADMIN_USERNAME).exists():
    User.objects.create_superuser(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD
    )
    print(f"Superuser '{ADMIN_USERNAME}' created.")
else:
    print(f"Superuser '{ADMIN_USERNAME}' already exists.")
