from django.contrib import admin
from .models import UserProfile, TravelInterest, PreferredDestination, DestinationTravelInterest, Trip, TravelBuddyRequest, UserPreferences, ChatMessage, TripReview, Subscription, TripNotification, ChatNotification
from django.utils import timezone

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'display_full_name', 'gender', 'dob', 'phone_number', 'profile_picture')
    list_filter = ('gender',)
    search_fields = ('username', 'email', 'full_name', 'phone_number')
    fieldsets = (
        ('Personal Information', {
            'fields': ('username', 'email', 'password', 'gender', 'dob', 'phone_number', 'profile_picture', 'full_name')
        }),
    )

    def display_full_name(self, obj):
        return obj.full_name if obj.full_name else "Not Set"
    display_full_name.short_description = 'Full Name'

class TravelInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'has_image', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True

class DestinationTravelInterestInline(admin.TabularInline):
    model = DestinationTravelInterest
    extra = 1
    autocomplete_fields = ['interest']

class PreferredDestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'has_image', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description', 'location', 'highlights')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DestinationTravelInterestInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image')
        }),
        ('Location Details', {
            'fields': ('location', 'highlights', 'best_time_to_visit')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = 'Has Image'

class DestinationTravelInterestAdmin(admin.ModelAdmin):
    list_display = ('destination', 'interest', 'created_at', 'updated_at')
    list_filter = ('destination', 'interest', 'created_at', 'updated_at')
    search_fields = ('destination__name', 'interest__name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['destination', 'interest']
    fieldsets = (
        ('Relationship', {
            'fields': ('destination', 'interest', 'description')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class TripAdmin(admin.ModelAdmin):
    list_display = ('user', 'destination', 'start_date', 'end_date', 'status', 'max_members', 'current_members', 'cancelled_by_display')
    list_filter = ('status', 'start_date', 'end_date', 'destination', 'cancelled_by')
    search_fields = ('user__username', 'destination__name', 'cancelled_by__username')
    filter_horizontal = ('activities', 'members')
    readonly_fields = ('created_at', 'cancelled_at')
    fieldsets = (
        ('Trip Information', {
            'fields': ('user', 'destination', 'activities', 'start_date', 'end_date')
        }),
        ('Buddy System', {
            'fields': ('max_members', 'members', 'status')
        }),
        ('Cancellation Information', {
            'fields': ('cancelled_by', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def cancelled_by_display(self, obj):
        if obj.cancelled_by:
            return obj.cancelled_by.username
        return '-'
    cancelled_by_display.short_description = 'Cancelled By'

    def current_members(self, obj):
        """Display current number of members"""
        return obj.members.count()
    current_members.short_description = 'Current Members'

    def save_model(self, request, obj, form, change):
        """Update status based on member count"""
        super().save_model(request, obj, form, change)
        if obj.members.count() >= obj.max_members:
            obj.status = 'full'
        else:
            obj.status = 'open'
        obj.save()

class TravelBuddyRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'trip', 'status', 'created_at', 'response_date')
    list_filter = ('status', 'created_at', 'response_date')
    search_fields = ('from_user__username', 'to_user__username', 'message')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Request Details', {
            'fields': ('from_user', 'to_user', 'trip', 'message')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """
        Allow admins to delete buddy requests.
        """
        return request.user.is_superuser

class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'travel_frequency', 'travel_budget')
    list_filter = ('travel_frequency', 'travel_budget')
    search_fields = ('user__username',)
    fieldsets = (
        ('User Preferences', {
            'fields': ('user', 'travel_frequency', 'travel_budget')
        }),
    )

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'trip', 'short_message', 'timestamp')
    list_filter = ('trip', 'sender', 'timestamp')
    search_fields = ('sender__username', 'message')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Message Details', {
            'fields': ('sender', 'trip', 'message', 'timestamp')
        }),
    )
    
    def short_message(self, obj):
        """Display shortened message in list view"""
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'

# Register your models here.
class TripReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'trip', 'rating', 'comment', 'created_at', 'updated_at')
    list_filter = ('rating', 'created_at', 'updated_at')
    search_fields = ('user__username', 'trip__destination__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fieldsets = (
        ('Review Details', {
            'fields': ('user', 'trip', 'rating', 'comment')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(TravelInterest, TravelInterestAdmin)
admin.site.register(PreferredDestination, PreferredDestinationAdmin)
admin.site.register(DestinationTravelInterest, DestinationTravelInterestAdmin)
admin.site.register(Trip, TripAdmin)
admin.site.register(TravelBuddyRequest, TravelBuddyRequestAdmin)

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('plan', 'is_active', 'start_date', 'end_date', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'plan', 'start_date', 'end_date', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """
        Only allow superusers to delete subscriptions
        """
        return request.user.is_superuser

class TripNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'trip', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'trip__destination__name', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'trip', 'notification_type', 'message', 'related_user', 'is_read')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

admin.site.register(UserPreferences, UserPreferencesAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(TripReview, TripReviewAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(TripNotification, TripNotificationAdmin)

class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'trip', 'sender', 'message_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'trip__destination__name', 'sender__username', 'message_preview')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'trip', 'chat_message', 'sender', 'message_preview', 'is_read')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

admin.site.register(ChatNotification, ChatNotificationAdmin)
