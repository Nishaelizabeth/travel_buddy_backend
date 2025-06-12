@echo off
echo Starting WebSocket-only server on port 8001...
echo.
echo This server will handle only WebSocket connections on port 8001.
echo Your regular Django server should be running on port 8000 for HTTP requests.
echo Press Ctrl+C to stop the server.
echo.

set DJANGO_SETTINGS_MODULE=travel_buddy_backend.settings
python websocket_only_server.py
