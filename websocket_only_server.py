import os
import sys
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('websocket_only_server')

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_buddy_backend.settings')
print(f"Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

# Setup Django
try:
    django.setup()
    print("Django setup completed successfully")
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

# Import after Django setup
from auth_app.middleware import JwtAuthMiddlewareStack
from auth_app.routing import websocket_urlpatterns

# Create a WebSocket-only application
websocket_application = ProtocolTypeRouter({
    # Only handle WebSocket protocol
    'websocket': JwtAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

# Print available routes
print("Available WebSocket routes:")
for route in websocket_urlpatterns:
    print(f"  {route}")

if __name__ == "__main__":
    import uvicorn
    
    # Run the server on port 8001 (different from Django's 8000)
    print("Starting WebSocket-only server on port 8001...")
    uvicorn.run(websocket_application, host="0.0.0.0", port=8001)
