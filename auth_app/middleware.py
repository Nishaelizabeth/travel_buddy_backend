from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

# Import Django-specific components inside functions to avoid early imports
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class JwtAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in WebSocket connections.
    """
    
    async def __call__(self, scope, receive, send):
        # Get the query string from the scope
        query_params = parse_qs(scope["query_string"].decode())
        token = query_params.get("token", [None])[0]
        
        if token:
            # Authenticate using the token
            try:
                # Verify the token and get the user
                user = await self.get_user_from_token(token)
                scope["user"] = user
            except (InvalidToken, TokenError) as e:
                scope["user"] = AnonymousUser()
        else:
            # No token provided
            scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        # Decode the token
        access_token = AccessToken(token)
        user_id = access_token["user_id"]
        
        # Get the user model dynamically
        UserModel = get_user_model()
        
        # Get the user from the database
        try:
            return UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return AnonymousUser()


def JwtAuthMiddlewareStack(inner):
    """
    Helper function to wrap an ASGI application with the JwtAuthMiddleware.
    This is similar to AuthMiddlewareStack but uses JWT tokens from query params.
    """
    from channels.auth import AuthMiddleware, AuthMiddlewareStack
    from channels.db import database_sync_to_async
    
    return JwtAuthMiddleware(inner)
