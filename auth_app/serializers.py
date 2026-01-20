from rest_framework import serializers
from .models import UserProfile, TravelInterest, PreferredDestination, DestinationTravelInterest, Trip, TravelBuddyRequest, UserPreferences, ChatMessage, TripReview, TripNotification, ChatNotification
from django.conf import settings
from . import views
from django.utils import timezone

class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'password', 'gender', 'dob', 'phone_number', 'profile_picture', 'full_name', 'is_staff', 'is_superuser']
        extra_kwargs = {
            'password': {'write_only': True},
            'full_name': {'required': False},
            'gender': {'required': False},
            'dob': {'required': False},
            'phone_number': {'required': False},
            'is_staff': {'read_only': True},
            'is_superuser': {'read_only': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Format the profile picture URL
        if instance.profile_picture and instance.profile_picture.name:
            if instance.profile_picture.url.startswith('http'):
                ret['profile_picture'] = instance.profile_picture.url
            else:
                ret['profile_picture'] = f"http://localhost:8000/media/{instance.profile_picture.name}"
        else:
            ret['profile_picture'] = None
            
        # Explicitly include phone number
        ret['phone_number'] = instance.phone_number
        
        return ret

    def create(self, validated_data):
        # Extract profile picture if present
        profile_picture = None
        if 'profile_picture' in validated_data:
            profile_picture = validated_data.pop('profile_picture')
        elif 'profile_picture' in self.context.get('request', {}).FILES:
            profile_picture = self.context.get('request').FILES['profile_picture']
            
        # Create user without profile picture first
        user = UserProfile(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        
        # Set profile picture after user is created
        if profile_picture:
            user.profile_picture = profile_picture
            user.save(update_fields=['profile_picture'])
            
        return user


class UserProfileCompatibilitySerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile that includes compatibility score with a reference trip.
    """
    profile_picture = serializers.SerializerMethodField()
    compatibility_score = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'profile_picture', 'gender', 'compatibility_score']

    def get_profile_picture(self, obj):
        """
        Get the URL of the profile picture, if it exists.
        """
        if obj.profile_picture:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.profile_picture.url)
        return None

    def get_compatibility_score(self, obj):
        """
        Calculate compatibility score between this user and the reference user's trip.
        
        The reference trip must be provided in the context as 'reference_trip'.
        """
        reference_trip = self.context.get('reference_trip')
        if not reference_trip:
            return 0
            
        # Get one of the user's trips to the same destination
        user_trips = Trip.objects.filter(
            user=obj,
            destination=reference_trip.destination
        ).exclude(id=reference_trip.id)
        
        if not user_trips.exists():
            return 0
            
        # Calculate compatibility score with the first matching trip
        return views.calculate_compatibility_score(reference_trip, user_trips.first())


class TravelInterestSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TravelInterest
        fields = ['id', 'name', 'description', 'image', 'image_url', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            # Fallback to constructing the URL manually
            return f"http://localhost:8000{obj.image.url}"
        return None

class PreferredDestinationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PreferredDestination
        fields = ['id', 'name', 'description', 'image', 'image_url', 'location', 'highlights', 'best_time_to_visit', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

class DestinationTravelInterestSerializer(serializers.ModelSerializer):
    interest_name = serializers.CharField(source='interest.name', read_only=True)
    interest_image = serializers.ImageField(source='interest.image', read_only=True)
    
    class Meta:
        model = DestinationTravelInterest
        fields = ['id', 'interest', 'interest_name', 'interest_image', 'description']

class PreferredDestinationDetailSerializer(serializers.ModelSerializer):
    travel_interests = serializers.SerializerMethodField()

    class Meta:
        model = PreferredDestination
        fields = ['id', 'name', 'description', 'image', 'location', 'highlights', 'best_time_to_visit', 'travel_interests']

    def get_travel_interests(self, obj):
        # Get all travel interests linked to this destination
        destination_interests = DestinationTravelInterest.objects.filter(destination=obj)
        interests = []
        for di in destination_interests:
            interests.append({
                'id': di.interest.id,
                'name': di.interest.name,
                'description': di.interest.description,
                'image': di.interest.image.url if di.interest.image else None,
                'destination_description': di.description
            })
        return interests

class TripSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    destination_location = serializers.CharField(source='destination.location', read_only=True)
    activities = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    cancelled_by_info = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ['id', 'user', 'destination', 'destination_name', 'destination_location', 
                'activities', 'start_date', 'end_date', 'status', 'cancelled_by_info']

    def get_activities(self, obj):
        try:
            return [{
                'id': activity.id,
                'name': activity.name,
                'description': activity.description
            } for activity in obj.activities.all()]
        except Exception as e:
            return []
    
    def get_cancelled_by_info(self, obj):
        if obj.status == 'cancelled' and obj.cancelled_by:
            return {
                'id': obj.cancelled_by.id,
                'username': obj.cancelled_by.username,
                'is_creator': obj.creator.id == obj.cancelled_by.id,
                'cancelled_at': obj.cancelled_at
            }
        return None
        
    def get_status(self, obj):
        # IMPORTANT: Always return the actual database status for cancelled trips
        if obj.status == 'cancelled':
            return 'cancelled'
            
        # For non-cancelled trips, calculate status based on dates
        current_date = timezone.now()
        if obj.end_date < current_date:
            return 'completed'
        elif obj.start_date > current_date:
            return 'upcoming'
        else:
            return 'ongoing'

class TravelBuddyRequestSerializer(serializers.ModelSerializer):
    from_user = UserProfileSerializer(read_only=True)
    to_user = UserProfileSerializer(read_only=True)
    trip = TripSerializer(read_only=True)

    class Meta:
        model = TravelBuddyRequest
        fields = [
            'id', 
            'from_user', 
            'to_user', 
            'trip', 
            'status', 
            'created_at'
        ]
        depth = 1

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add nested trip fields for easier frontend access
        trip = data.get('trip', {})
        data['destination_name'] = trip.get('destination_name', '')
        data['destination_location'] = trip.get('destination_location', '')
        data['start_date'] = trip.get('start_date')
        data['end_date'] = trip.get('end_date')
        data['activities'] = trip.get('activities', [])
        return data

class UserPreferencesSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = UserPreferences
        fields = ['id', 'user', 'travel_frequency', 'travel_budget']
        depth = 1

class BuddyProfileSerializer(serializers.ModelSerializer):
    travel_budget = serializers.SerializerMethodField()
    travel_frequency = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()
    activities = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    trip_id = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'username',
            'email',
            'profile_picture',
            'gender',
            'travel_budget',
            'travel_frequency',
            'destination',
            'activities',
            'start_date',
            'end_date',
            'trip_id'
        ]

    def get_travel_budget(self, obj):
        try:
            return obj.preferences.travel_budget if hasattr(obj, 'preferences') else None
        except UserPreferences.DoesNotExist:
            return None

    def get_travel_frequency(self, obj):
        try:
            return obj.preferences.travel_frequency if hasattr(obj, 'preferences') else None
        except UserPreferences.DoesNotExist:
            return None

    def get_trip_id(self, obj):
        try:
            trip = Trip.objects.filter(user=obj).latest('start_date')
            return trip.id
        except Trip.DoesNotExist:
            return None

    def get_destination(self, obj):
        try:
            trip = Trip.objects.filter(user=obj).latest('start_date')
            return trip.destination.name
        except (Trip.DoesNotExist, AttributeError):
            return None

    def get_activities(self, obj):
        try:
            trip = Trip.objects.filter(user=obj).latest('start_date')
            return [activity.name for activity in trip.activities.all()]
        except (Trip.DoesNotExist, AttributeError):
            return []

    def get_start_date(self, obj):
        try:
            trip = Trip.objects.filter(user=obj).latest('start_date')
            return trip.start_date.strftime('%Y-%m-%d')
        except (Trip.DoesNotExist, AttributeError):
            return None

    def get_end_date(self, obj):
        try:
            trip = Trip.objects.filter(user=obj).latest('start_date')
            return trip.end_date.strftime('%Y-%m-%d')
        except (Trip.DoesNotExist, AttributeError):
            return None

    def get_profile_picture(self, obj):
        if obj.profile_picture and obj.profile_picture.name:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            # Return just the path relative to media/
            return obj.profile_picture.url
        return None

class CreatorInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for basic creator information.
    """
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'profile_picture']

class CompatibleTripSerializer(serializers.ModelSerializer):
    """
    Serializer for compatible trips including compatibility score.
    """
    destination = serializers.SerializerMethodField()
    activities = serializers.SerializerMethodField()
    creator = CreatorInfoSerializer(read_only=True, source='user')
    compatibility_score = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            'id',
            'destination',
            'activities',
            'start_date',
            'end_date',
            'creator',
            'compatibility_score'
        ]

    def get_compatibility_score(self, obj):
        """
        Get the compatibility score from the context.
        """
        scores = self.context.get('compatibility_scores', {})
        return scores.get(int(obj.id), 0)

    def get_destination(self, obj):
        """
        Get destination details including name and image.
        """
        return {
            'id': obj.destination.id,
            'name': obj.destination.name,
            'image': obj.destination.image.url if obj.destination.image else None
        }

    def get_activities(self, obj):
        """
        Get list of activity names.
        """
        return [
            {
                'id': activity.id,
                'name': activity.name,
                'image': activity.image.url if activity.image else None
            }
            for activity in obj.activities.all()
        ]

class MyBuddiesSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying trips and their confirmed buddies.
    """
    buddies = serializers.SerializerMethodField()
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    destination_location = serializers.CharField(source='destination.location', read_only=True)
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    buddy_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ['id', 'destination_name', 'destination_location', 'start_date', 'end_date', 'buddies', 'buddy_count']

    def get_buddies(self, obj):
        """
        Get the list of buddies for this trip.
        """
        if hasattr(obj, 'buddies'):
            buddy_serializer = UserProfileSerializer(
                obj.buddies,
                many=True,
                context={'request': self.context.get('request')}
            )
            return buddy_serializer.data
        return []

    def get_buddy_count(self, obj):
        """
        Get the number of buddies for this trip.
        """
        return getattr(obj, 'buddy_count', 0)

    def get_start_date(self, obj):
        """
        Get the start date as a string in YYYY-MM-DD format.
        """
        if obj.start_date:
            return obj.start_date.strftime('%Y-%m-%d')
        return None

    def get_end_date(self, obj):
        """
        Get the end date as a string in YYYY-MM-DD format.
        """
        if obj.end_date:
            return obj.end_date.strftime('%Y-%m-%d')
        return None

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'profile_picture']

class DestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreferredDestination
        fields = ['id', 'name', 'location', 'image']

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelInterest
        fields = ['id', 'name']

class TripDetailSerializer(serializers.ModelSerializer):
    destination = DestinationSerializer()
    creator = UserSerializer(source='user')
    members = UserSerializer(many=True)
    activities = ActivitySerializer(many=True)

    class Meta:
        model = Trip
        fields = [
            'id',
            'destination',
            'creator',
            'members',
            'activities',
            'start_date',
            'end_date',
            'description',
            'status',
            'max_members'
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_profile_picture = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ['id', 'trip', 'sender', 'sender_username', 'sender_profile_picture', 'message', 'timestamp', 'formatted_timestamp']
        read_only_fields = ['sender', 'timestamp']
    
    def get_sender_profile_picture(self, obj):
        if obj.sender.profile_picture:
            return f"http://localhost:8000{obj.sender.profile_picture.url}"
        return None
    
    def get_formatted_timestamp(self, obj):
        # Format timestamp as a human-readable string
        return obj.timestamp.strftime('%b %d, %Y %I:%M %p')
    
    def create(self, validated_data):
        # Set the sender to the current user
        user = self.context['request'].user
        validated_data['sender'] = user
        return super().create(validated_data)


class TripReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_profile_picture = serializers.SerializerMethodField()
    trip_name = serializers.CharField(source='trip.destination.name', read_only=True)
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = TripReview
        fields = ['id', 'user', 'user_name', 'user_profile_picture', 'trip', 'trip_name', 
                 'rating', 'comment', 'created_at', 'formatted_date']
        read_only_fields = ['user', 'created_at']
    
    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            return f"http://localhost:8000{obj.user.profile_picture.url}"
        return None
    
    def get_formatted_date(self, obj):
        # Format date as a human-readable string
        return obj.created_at.strftime('%b %d, %Y')
    
    def create(self, validated_data):
        # Set the user to the current user
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Check if a review already exists for this user and trip
        existing_review = TripReview.objects.filter(
            user=user, 
            trip=validated_data['trip']
        ).first()
        
        if existing_review:
            # Update the existing review
            existing_review.rating = validated_data['rating']
            existing_review.comment = validated_data.get('comment', '')
            existing_review.save()
            return existing_review
        
        # Create a new review
        return super().create(validated_data)


class TripNotificationSerializer(serializers.ModelSerializer):
    trip_name = serializers.CharField(source='trip.destination.name', read_only=True)
    related_user_name = serializers.SerializerMethodField()
    related_user_picture = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = TripNotification
        fields = [
            'id', 'user', 'trip', 'trip_name', 'notification_type', 'message',
            'related_user_name', 'related_user_picture', 'is_read', 'created_at', 'formatted_date'
        ]
        read_only_fields = ['user', 'created_at']
    
    def get_related_user_name(self, obj):
        if obj.related_user:
            return obj.related_user.username
        return None
    
    def get_related_user_picture(self, obj):
        if obj.related_user and obj.related_user.profile_picture:
            return f"http://localhost:8000{obj.related_user.profile_picture.url}"
        return None
    
    def get_formatted_date(self, obj):
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')


class ChatNotificationSerializer(serializers.ModelSerializer):
    trip_name = serializers.CharField(source='trip.destination.name', read_only=True)
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_picture = serializers.SerializerMethodField()
    formatted_date = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'user', 'trip', 'trip_name', 'chat_message', 'sender', 'sender_name',
            'sender_picture', 'message_preview', 'is_read', 'created_at', 'formatted_date'
        ]
        read_only_fields = ['user', 'created_at']
    
    def get_sender_picture(self, obj):
        if obj.sender and obj.sender.profile_picture:
            return f"http://localhost:8000{obj.sender.profile_picture.url}"
        return None
    
    def get_formatted_date(self, obj):
        return obj.created_at.strftime('%B %d, %Y at %I:%M %p')