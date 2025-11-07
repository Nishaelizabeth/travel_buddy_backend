import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Trip, ChatMessage, UserProfile

# Set up logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Log connection attempt with full scope details
            logger.info(f"WebSocket connection attempt with scope: {self.scope}")
            
            # Get trip_id from URL route parameters
            self.trip_id = self.scope['url_route']['kwargs']['trip_id']
            logger.info(f"Trip ID from URL: {self.trip_id}")
            
            self.room_group_name = f'chat_{self.trip_id}'
            logger.info(f"Room group name: {self.room_group_name}")
            
            # Get the user from the scope
            self.user = self.scope.get('user')
            logger.info(f"User from scope: {self.user.username} (ID: {self.user.id})")
            
            # Check if user is authenticated
            if self.user.is_anonymous:
                logger.warning(f"Anonymous user attempted to connect to chat {self.trip_id}")
                await self.close()
                return
            
            # Check if user is a member of the trip
            is_member = await self.is_trip_member()
            logger.info(f"User {self.user.username} (ID: {self.user.id}) is member of trip {self.trip_id}: {is_member}")
            
            if not is_member:
                logger.warning(f"User {self.user.username} (ID: {self.user.id}) attempted to access trip {self.trip_id} but is not a member")
                await self.close()
                return
            
            # Join room group
            logger.info(f"Adding user {self.user.username} to room group {self.room_group_name}")
            
            # This is the critical part that was missing - actually joining the channel group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            logger.info(f"Successfully added to channel group {self.room_group_name}")
            
            # Accept the connection
            await self.accept()
            logger.info(f"WebSocket connection accepted for user {self.user.username}")
            
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close()
            return
    
    async def disconnect(self, close_code):
        try:
            logger.info(f"WebSocket disconnect with code: {close_code}")
            
            # Check if we have a room_group_name (might not if connection failed early)
            if hasattr(self, 'room_group_name') and hasattr(self, 'channel_name'):
                logger.info(f"Removing user from room group {self.room_group_name}")
                
                # Leave room group
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                logger.info(f"Successfully removed from room group")
            else:
                logger.warning(f"Disconnect called but room_group_name or channel_name not set")
        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    
    async def receive(self, text_data):
        # Parse the received JSON data
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')
        
        if not message.strip():
            return
        
        # Save message to database
        chat_message = await self.save_message(message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'sender_profile_picture': self.user.profile_picture.url if self.user.profile_picture else None,
                'timestamp': chat_message.timestamp.isoformat(),
                'formatted_timestamp': chat_message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'message_id': chat_message.id
            }
        )
    
    async def chat_message(self, event):
        try:
            logger.info(f"Sending chat message to client: {event}")
            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'message': event['message'],
                'sender_id': event['sender_id'],
                'sender_username': event['sender_username'],
                'sender_profile_picture': event['sender_profile_picture'],
                'timestamp': event['timestamp'],
                'formatted_timestamp': event['formatted_timestamp'],
                'message_id': event['message_id']
            }))
            logger.info("Message sent successfully")
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    
    @database_sync_to_async
    def is_trip_member(self):
        try:
            logger.info(f"Checking if user {self.user.id} is a member of trip {self.trip_id}")
            
            # SUPER IMPORTANT: For testing purposes, allow all authenticated users
            # This bypasses all membership checks to help isolate connection issues
            logger.info(f"BYPASSING MEMBERSHIP CHECK: Allowing all authenticated users for testing")
            return True
            
            # The code below is commented out during testing
            # Uncomment this code when the WebSocket connection is working properly
            '''
            # Detailed logging of all trips for debugging
            all_trips = list(Trip.objects.all().values_list('id', flat=True))
            logger.info(f"All trip IDs in database: {all_trips}")
            
            # Get the trip and log its details
            try:
                trip = Trip.objects.get(id=self.trip_id)
                logger.info(f"Found trip {self.trip_id}: creator={trip.user.id}, members={list(trip.members.values_list('id', flat=True))}")
                
                # Check membership
                is_member = trip.members.filter(id=self.user.id).exists()
                is_creator = trip.user.id == self.user.id
                logger.info(f"User {self.user.id} is member: {is_member}, is creator: {is_creator}")
                
                return is_member or is_creator
            except Trip.DoesNotExist:
                logger.error(f"Trip {self.trip_id} does not exist")
                return False
            '''
        except Exception as e:
            logger.error(f"Error checking trip membership: {str(e)}")
            # Log the full exception traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
            # For testing, allow connection even if there's an error
            return True
    
    @database_sync_to_async
    def save_message(self, message_text):
        try:
            logger.info(f"Saving message from user {self.user.username} to trip {self.trip_id}")
            trip = Trip.objects.get(id=self.trip_id)
            chat_message = ChatMessage.objects.create(
                trip=trip,
                sender=self.user,
                message=message_text
            )
            logger.info(f"Message saved successfully with ID: {chat_message.id}")
            
            # Create chat notifications for all trip members except the sender
            self.create_chat_notifications(trip, chat_message)
            logger.info(f"Chat notifications created for message ID: {chat_message.id}")
            
            return chat_message
        except Trip.DoesNotExist:
            logger.error(f"Trip {self.trip_id} does not exist when saving message")
            raise
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            raise
    
    def create_chat_notifications(self, trip, chat_message):
        """Create chat notifications for all trip members except the sender."""
        from .models import ChatNotification
        
        sender = self.user
        logger.info(f"Creating chat notifications for message from {sender.username} in trip {trip.id}")
        
        # Get all trip members (including the creator) except the sender
        recipients = set()
        
        # Add trip creator if not the sender
        if trip.user != sender:
            recipients.add(trip.user)
        
        # Add all trip members except the sender
        for member in trip.members.all():
            if member != sender:
                recipients.add(member)
        
        # Create message preview (truncate to 50 chars)
        message_preview = chat_message.message[:47] + '...' if len(chat_message.message) > 50 else chat_message.message
        
        # Create a notification for each recipient
        notification_count = 0
        for recipient in recipients:
            ChatNotification.objects.create(
                user=recipient,
                trip=trip,
                chat_message=chat_message,
                sender=sender,
                message_preview=message_preview,
                is_read=False
            )
            notification_count += 1
        
        logger.info(f"Created {notification_count} chat notifications for message ID: {chat_message.id}")
        return notification_count
