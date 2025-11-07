@echo off
echo Starting Django server with Daphne for WebSocket support...
echo.
echo This server will handle both HTTP and WebSocket connections on port 8000.
echo Press Ctrl+C to stop the server.
echo.

set DJANGO_SETTINGS_MODULE=travel_buddy_backend.settings
daphne -b 0.0.0.0 -p 8000 travel_buddy_backend.asgi:application
