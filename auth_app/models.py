from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class UserProfile(AbstractUser):
    """Custom User Model with additional fields for user details."""
    
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_discoverable = models.BooleanField(default=True, help_text="Whether this user can be discovered by other users")

    def __str__(self):
        return self.username


class TravelInterest(models.Model):
    """Admin-defined Travel Interests"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='travel_interests/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PreferredDestination(models.Model):
    """Admin-defined Preferred Destinations"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='destinations/', blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    highlights = models.TextField(blank=True, null=True)
    best_time_to_visit = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DestinationTravelInterest(models.Model):
    """Travel interests specific to each preferred destination"""
    
    destination = models.ForeignKey(PreferredDestination, on_delete=models.CASCADE, related_name='travel_interests')
    interest = models.ForeignKey(TravelInterest, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['destination', 'interest']
        unique_together = ['destination', 'interest']

    def __str__(self):
        return f"{self.destination.name} - {self.interest.name}"


class Trip(models.Model):
    """Model for storing trip details"""
    
    TRIP_STATUS_CHOICES = [
        ('open', 'Open'),
        ('full', 'Full'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='trips')
    destination = models.ForeignKey(PreferredDestination, on_delete=models.CASCADE)
    activities = models.ManyToManyField(TravelInterest)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_members = models.PositiveIntegerField(
        help_text="Total number of travelers allowed on this trip including the creator"
    )
    members = models.ManyToManyField(
        UserProfile,
        related_name='joined_trips',
        blank=True,
        help_text="Users who have joined this trip"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the trip"
    )
    status = models.CharField(
        max_length=10,
        choices=TRIP_STATUS_CHOICES,
        default='open',
        db_index=True,  # Add index for faster filtering by status
        help_text="Status of the trip"
    )
    cancelled_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        related_name='cancelled_trips',
        blank=True,
        null=True,
        help_text="User who cancelled the trip"
    )
    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the trip was cancelled"
    )
    created_at = models.DateTimeField(
    auto_now_add=True,
    help_text="Timestamp when the trip was created"
    )
    is_cancelled = models.BooleanField(
        default=False,
        db_index=True,  # Add index for faster filtering
        help_text="Flag to quickly identify cancelled trips"
    )

    def __str__(self):
        return f"Trip to {self.destination.name} ({self.start_date.date()} - {self.end_date.date()})"

    @property
    def creator(self):
        return self.user

    def is_full(self):
        """Check if the trip has reached its member limit"""
        return self.members.count() >= self.max_members

    def can_join(self, user):
        """Check if a user can join this trip"""
        if self.is_full():
            return False
        if self.status == 'completed':
            return False
        if user in self.members.all():
            return False
        return True

    def add_member(self, user):
        """Add a member to the trip if possible"""
        if not self.can_join(user):
            raise ValueError("Cannot add member: " + (
                "Trip is full" if self.is_full() else
                "Trip has completed" if self.status == 'completed' else
                "User is already a member"
            ))
        
        self.members.add(user)
        self.save()  # This will update the status if needed

    def save(self, *args, **kwargs):
        """Update status based on member count and trip dates"""
        if self.pk:  # Only update status for existing trips
            current_members = self.members.count()
            
            # Update status based on member count
            if current_members >= self.max_members:
                self.status = 'full'
            elif self.status == 'full' and current_members < self.max_members:
                self.status = 'open'
            
            # Update status based on trip dates
            if self.end_date and self.end_date < timezone.now() and self.status != 'cancelled':
                self.status = 'completed'
            
            # Update is_cancelled flag based on status
            if self.status == 'cancelled':
                self.is_cancelled = True
            
            # Ensure status is valid if not cancelled
            if self.status not in ['open', 'full', 'completed', 'cancelled']:
                self.status = 'open'
        
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-start_date']


class TravelBuddyRequest(models.Model):
    """Model for managing travel buddy requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    from_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_requests')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='buddy_requests')
    message = models.TextField(blank=True, null=True)  # Optional message when sending a request
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    response_date = models.DateTimeField(blank=True, null=True)  # Track when accepted/rejected

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['from_user', 'to_user', 'trip'], name="unique_buddy_request")
        ]

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"

    def accept(self):
        """Accept the buddy request"""
        self.status = 'accepted'
        self.response_date = timezone.now()
        self.save()

    def reject(self):
        """Reject the buddy request"""
        self.status = 'rejected'
        self.response_date = timezone.now()
        self.save()

    @property
    def is_pending(self):
        """Check if the request is still pending"""
        return self.status == 'pending'

    @property
    def is_accepted(self):
        """Check if the request has been accepted"""
        return self.status == 'accepted'

    @property
    def is_rejected(self):
        """Check if the request has been rejected"""
        return self.status == 'rejected'


class UserPreferences(models.Model):
    """Model to store user travel preferences (budget & frequency)."""
    
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='preferences')
    
    TRAVEL_FREQUENCY_CHOICES = [
        ('Rarely', 'Rarely'),
        ('Occasionally', 'Occasionally'),
        ('Frequently', 'Frequently')
    ]
    TRAVEL_BUDGET_CHOICES = [
        ('low', 'Budget-Friendly'),
        ('medium', 'Moderate'),
        ('high', 'Luxury'),
    ]

    travel_frequency = models.CharField(
        max_length=20,
        choices=TRAVEL_FREQUENCY_CHOICES,
        blank=True,
        null=True,
        help_text="How often you like to travel"
    )
    travel_budget = models.CharField(
        max_length=10,
        choices=TRAVEL_BUDGET_CHOICES,
        blank=True,
        null=True,
        help_text="Your preferred travel budget range"
    )

    class Meta:
        verbose_name = "User Preferences"
        verbose_name_plural = "User Preferences"

    def __str__(self):
        return f"{self.user.username}'s preferences"


class ChatMessage(models.Model):
    """Model for storing chat messages between trip members."""
    
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
    
    def __str__(self):
        return f"{self.sender.username} in {self.trip}: {self.message[:30]}"


class TripReview(models.Model):
    """Model for storing user reviews for completed trips."""
    
    RATING_CHOICES = [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='reviews')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trip Review"
        verbose_name_plural = "Trip Reviews"
        constraints = [
            models.UniqueConstraint(fields=['user', 'trip'], name="unique_user_trip_review")
        ]
    
    def __str__(self):
        return f"{self.user.username}'s review for {self.trip.destination.name}"


class TripNotification(models.Model):
    """Model for storing trip-related notifications for users."""
    
    NOTIFICATION_TYPES = [
        ('trip_cancelled', 'Trip Cancelled'),
        ('new_member', 'New Member Joined'),
        ('trip_joined', 'Successfully Joined Trip'),
        ('trip_left', 'Member Left Trip'),
        ('trip_updated', 'Trip Details Updated'),
        ('review_reminder', 'Review Reminder')
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='trip_notifications')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    related_user = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='related_notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Trip Notification"
        verbose_name_plural = "Trip Notifications"
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class ChatNotification(models.Model):
    """Model for storing chat-related notifications for users."""
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='chat_notifications')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='chat_notifications')
    chat_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(
        UserProfile, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sent_chat_notifications'
    )
    message_preview = models.CharField(max_length=50, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Chat Notification"
        verbose_name_plural = "Chat Notifications"
    
    def __str__(self):
        return f"{self.user.username} - Message from {self.sender.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class Subscription(models.Model):
    """Model to store premium user subscription details"""
    
    PLAN_CHOICES = [
        ('silver', 'Silver Plan (Monthly)'),
        ('gold', 'Gold Plan (Annual)')
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_plan_display()}"
    
    def save(self, *args, **kwargs):
        # Set end_date based on plan if not already set
        if not self.end_date:
            if self.plan == 'silver':
                self.end_date = self.start_date + timezone.timedelta(days=30)
            elif self.plan == 'gold':
                self.end_date = self.start_date + timezone.timedelta(days=365)
        super().save(*args, **kwargs)
