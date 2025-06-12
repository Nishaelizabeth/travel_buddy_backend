"""
ASGI config for travel_buddy_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django

# Set Django settings module explicitly
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_buddy_backend.settings')

# Setup Django first - this is critical
django.setup()

# Import Django ASGI application - must be after django.setup()
from django.core.asgi import get_asgi_application

# Now import Channels and routing components after Django is fully loaded
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Custom auth middleware - import after Django setup
from auth_app.middleware import JwtAuthMiddlewareStack

# Import websocket routing
from auth_app.routing import websocket_urlpatterns

# Configure the ASGI application
application = ProtocolTypeRouter({
    # Django's ASGI application for handling HTTP requests
    'http': get_asgi_application(),
    
    # WebSocket handler with JWT authentication middleware
    'websocket': JwtAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
