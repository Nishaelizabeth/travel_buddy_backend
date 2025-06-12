from django.urls import path, re_path
from . import consumers

# Define WebSocket URL patterns
websocket_urlpatterns = [
    # Simple pattern for chat WebSocket
    path('ws/chat/<int:trip_id>/', consumers.ChatConsumer.as_asgi()),
    
    # Alternative pattern using re_path for more flexibility
    # re_path(r'^ws/chat/(?P<trip_id>\d+)/?$', consumers.ChatConsumer.as_asgi()),
]

# These patterns will be used by the ASGI application in travel_buddy_backend/asgi.py
# to route WebSocket connections to the appropriate consumer
