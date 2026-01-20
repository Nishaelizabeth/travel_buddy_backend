from django.urls import path
from . import views
from .views import (UserRegistrationView, TravelInterestListView, 
                     PreferredDestinationListView, PreferredDestinationDetailView,
                     BuddyProfileView, SendBuddyRequestView, MyTripsView, HandleBuddyRequestView,
                     TripCreateView, CompatibleTripsView, JoinTripView, TripDetailsView, TripChatMessagesView,
                     UserStatsView, UserDashboardView, ConnectedBuddiesView, CancelTripView, LeaveTripView,
                     create_razorpay_order, verify_razorpay_payment, TripNotificationView, UnreadNotificationCountView,
                     ChatNotificationView, UnreadChatNotificationCountView, RemoveTripMemberView,
                     DestinationRecommendationsView)
# Import review views from views.py instead of review_views.py
from .views import TripReviewView, LatestReviewsView, test_review_endpoint
# Import admin views
from .views import (AdminStatsView, AdminUserListView, AdminUserDetailView,
                     AdminDestinationListView, AdminDestinationDetailView, AdminDestinationInterestsView,
                     AdminInterestListView, AdminInterestDetailView,
                     AdminDestinationInterestListView, AdminDestinationInterestDetailView,
                     AdminTripListView, AdminTripDetailView, AdminTripMembersView,
                     AdminReviewListView, AdminReviewDetailView)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('validate-field/', views.validate_field, name='validate-field'),
    path('login/', views.login_user, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('logout/', views.logout_user, name='logout'),
    path('update-profile/', views.update_profile, name='update-profile'),
    path('profile/', views.get_user_profile, name='user-profile'),
    path('update-preferences/', views.update_preferences, name='update-preferences'),
    path('travel-interests/', views.get_travel_interests, name='travel-interests'),
    path('destinations/', PreferredDestinationListView.as_view(), name='destinations'),
    path('destinations/<int:pk>/', PreferredDestinationDetailView.as_view(), name='destination-detail'),
    path('check-trip-dates/', views.check_trip_dates, name='check-trip-dates'),
    path('find-travel-buddies/', views.find_travel_buddies, name='find-travel-buddies'),
    path('send-buddy-request/', views.send_buddy_request, name='send-buddy-request'),
    path('handle-buddy-request/', HandleBuddyRequestView.as_view(), name='handle-buddy-request'),
    path('buddy-requests/', views.get_buddy_requests, name='buddy-requests'),
    path('save-trip/', views.save_trip, name='save-trip'),
    path('user-preferences/', views.user_preferences, name='user-preferences'),
    path('trips/', views.trips, name='trips'),
    path('trips/user/', views.user_trips, name='user-trips'),
    path('create-trip/', TripCreateView.as_view(), name='create-trip'),
    path('change-password/', views.change_password, name='change_password'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('my-trips/', MyTripsView.as_view(), name='my-trips'),
    path('my-buddies/', views.MyBuddiesView.as_view(), name='my-buddies'),
    path('buddy-profile/<int:user_id>/', BuddyProfileView.as_view(), name='buddy-profile'),
    path('send-buddy-request/<int:buddy_id>/', SendBuddyRequestView.as_view(), name='send-buddy-request'),
    path('compatible-trips/', CompatibleTripsView.as_view(), name='compatible-trips'),
    path('trip/<int:trip_id>/join/', JoinTripView.as_view(), name='join_trip'),
    path('join-trip/<int:trip_id>/', JoinTripView.as_view(), name='join_trip'),
    path('trip/<int:trip_id>/', TripDetailsView.as_view(), name='trip_details'),
    # Chat endpoints
    path('trip/<int:trip_id>/chat/', TripChatMessagesView.as_view(), name='trip_chat'),
    # User stats endpoint
    path('user-stats/', UserStatsView.as_view(), name='user-stats'),
    # User dashboard endpoint
    path('user-dashboard/', UserDashboardView.as_view(), name='user-dashboard'),
    # Review endpoints
    path('test-review-endpoint/', test_review_endpoint, name='test-review-endpoint'),
    path('trip-reviews/', TripReviewView.as_view(), name='trip-reviews'),
    path('latest-reviews/', LatestReviewsView.as_view(), name='latest-reviews'),
    
    # Admin API endpoints
    path('admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    
    # Admin User Management
    path('admin/users/', AdminUserListView.as_view(), name='admin-users-list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    # Admin Destination Management
    path('admin/destinations/', AdminDestinationListView.as_view(), name='admin-destinations-list'),
    path('admin/destinations/<int:pk>/', AdminDestinationDetailView.as_view(), name='admin-destination-detail'),
    path('admin/destinations/<int:pk>/interests/', AdminDestinationInterestsView.as_view(), name='admin-destination-interests'),
    
    # Admin Travel Interest Management
    path('admin/interests/', AdminInterestListView.as_view(), name='admin-interests-list'),
    path('admin/interests/<int:pk>/', AdminInterestDetailView.as_view(), name='admin-interest-detail'),
    
    # Admin Destination-Interest Mapping
    path('admin/destination-interests/', AdminDestinationInterestListView.as_view(), name='admin-destination-interests-list'),
    path('admin/destination-interests/<int:pk>/', AdminDestinationInterestDetailView.as_view(), name='admin-destination-interest-detail'),
    
    # Admin Trip Management
    path('admin/trips/', AdminTripListView.as_view(), name='admin-trips-list'),
    path('admin/trips/<int:pk>/', AdminTripDetailView.as_view(), name='admin-trip-detail'),
    path('admin/trips/<int:trip_id>/members/', AdminTripMembersView.as_view(), name='admin-trip-members'),
    
    # Admin Review Management
    path('admin/reviews/', AdminReviewListView.as_view(), name='admin-reviews-list'),
    path('admin/reviews/<int:pk>/', AdminReviewDetailView.as_view(), name='admin-review-detail'),
    # Connected buddies endpoint
    path('connected-buddies/', ConnectedBuddiesView.as_view(), name='connected-buddies'),
    # Trip cancellation and leaving endpoints
    path('trip/<int:trip_id>/cancel/', CancelTripView.as_view(), name='cancel-trip'),
    path('trip/<int:trip_id>/leave/', LeaveTripView.as_view(), name='leave-trip'),
    path('trip/<int:trip_id>/remove-member/<int:member_id>/', RemoveTripMemberView.as_view(), name='remove-trip-member'),
    
    # Razorpay payment endpoints
    path('create-razorpay-order/', create_razorpay_order, name='create-razorpay-order'),
    path('verify-razorpay-payment/', verify_razorpay_payment, name='verify-razorpay-payment'),
    path('check-subscription/', views.check_subscription, name='check-subscription'),
    
    # Trip Notification endpoints
    path('notifications/', TripNotificationView.as_view(), name='notifications'),
    path('notifications/unread-count/', UnreadNotificationCountView.as_view(), name='unread-notification-count'),
    
    # Chat Notification endpoints
    path('chat-notifications/', ChatNotificationView.as_view(), name='chat-notifications'),
    path('chat-notifications/unread-count/', UnreadChatNotificationCountView.as_view(), name='unread-chat-notification-count'),
    
    # AI / OpenTripMap Destination Recommendations
    path('ai/destination-recommendations/', DestinationRecommendationsView.as_view(), name='destination-recommendations'),
]
