from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import UserProfile, TravelInterest, PreferredDestination, Trip, TravelBuddyRequest, DestinationTravelInterest, UserPreferences, ChatMessage, TripReview, TripNotification, ChatNotification, Subscription
from .serializers import (UserProfileSerializer, TravelInterestSerializer, 
                       PreferredDestinationSerializer, PreferredDestinationDetailSerializer, TripSerializer,
                       TravelBuddyRequestSerializer, UserPreferencesSerializer, UserProfileCompatibilitySerializer, 
                       BuddyProfileSerializer, MyBuddiesSerializer, CompatibleTripSerializer, TripDetailSerializer,
                       ChatMessageSerializer, TripReviewSerializer, TripNotificationSerializer, ChatNotificationSerializer)
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db.models import Q, Count, F, Exists, OuterRef
import jwt
from django.conf import settings
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import logging
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from dateutil import parser
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import random
import string
from django.core.mail import send_mail

# Create a logger
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Handle forgot password requests.
    Generates a 6-digit code, sets it as the user's new password,
    and sends it to the user's email.
    """
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = UserProfile.objects.get(email=email)
        
        # Generate a 6-digit random code
        reset_code = ''.join(random.choices(string.digits, k=6))
        
        # Set the code as the user's new password
        user.set_password(reset_code)
        user.save()
        
        # Send the code to the user's email
        try:
            send_mail(
                'Password Reset Code - Travel Buddy',
                f'Your password reset code is: {reset_code}\n\nUse this code to login to your account.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({
                'message': 'Password reset code has been sent to your email'
            })
        except Exception as e:
            logger.error(f'Error sending email: {str(e)}')
            return Response({
                'error': 'Failed to send email. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'No account found with this email address'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f'Error in forgot_password: {str(e)}')
        return Response({
            'error': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Create your views here.

class UserRegistrationView(generics.CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        # Log the incoming request data for debugging
        logger.info(f"Registration request received")
        logger.info(f"Data in request: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            logger.info(f"User created successfully: {serializer.data.get('username')}")
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            return Response({
                'message': f'Registration failed: {str(e)}',
            }, status=status.HTTP_400_BAD_REQUEST)

class TravelInterestListView(generics.ListAPIView):
    queryset = TravelInterest.objects.all()
    serializer_class = TravelInterestSerializer
    permission_classes = [AllowAny]

class PreferredDestinationListView(generics.ListAPIView):
    queryset = PreferredDestination.objects.all()
    serializer_class = PreferredDestinationSerializer
    permission_classes = [AllowAny]

class PreferredDestinationDetailView(generics.RetrieveAPIView):
    queryset = PreferredDestination.objects.all()
    serializer_class = PreferredDestinationDetailSerializer
    permission_classes = [AllowAny]

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def validate_field(request):
    """
    Validate a single registration field in real-time.
    Accepts field_name and field_value in the request body.
    Returns whether the field is valid or not.
    """
    field_name = request.data.get('field_name')
    field_value = request.data.get('field_value')
    
    if not field_name or field_value is None:
        return Response({
            'valid': False,
            'message': 'Both field_name and field_value are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate username
    if field_name == 'username':
        if len(field_value.strip()) < 3:
            return Response({
                'valid': False,
                'message': 'Username must be at least 3 characters long'
            })
        
        # Check if username already exists
        if UserProfile.objects.filter(username=field_value).exists():
            return Response({
                'valid': False,
                'message': 'This username is already taken. Please choose another one.'
            })
    
    # Validate email
    elif field_name == 'email':
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', field_value):
            return Response({
                'valid': False,
                'message': 'Please enter a valid email address'
            })
            
        # Check if email already exists
        if UserProfile.objects.filter(email=field_value).exists():
            return Response({
                'valid': False,
                'message': 'This email address is already registered. Please use another one.'
            })
    
    # Validate phone number (if needed)
    elif field_name == 'phone_number':
        import re
        if field_value and not re.match(r'^\+?[0-9]{10,15}$', field_value):
            return Response({
                'valid': False,
                'message': 'Please enter a valid phone number'
            })
            
        # Check if phone number already exists (if it's supposed to be unique)
        if field_value and UserProfile.objects.filter(phone_number=field_value).exists():
            return Response({
                'valid': False,
                'message': 'This phone number is already registered. Please use another one.'
            })
    
    # Field is valid
    return Response({
        'valid': True,
        'message': 'Valid'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    # Log the incoming request data for debugging
    logger.info(f"Registration request received")
    logger.info(f"Files in request: {request.FILES}")
    logger.info(f"Data in request: {request.data}")
    
    try:
        # Create a mutable copy of the data
        data = request.data.copy() if hasattr(request.data, 'copy') else request.data
        
        # Pass the request in the context to the serializer
        user_serializer = UserProfileSerializer(data=data, context={'request': request})
        
        if user_serializer.is_valid():
            try:
                # Save the user with the serializer
                user = user_serializer.save()
                logger.info(f"User created successfully: {user.username}")
                
                # Double-check if profile picture was saved
                if user.profile_picture:
                    logger.info(f"Profile picture saved: {user.profile_picture.name}")
                else:
                    logger.warning("Profile picture was not saved")
                    
                    # Try to save it directly if it's in the request.FILES
                    if 'profile_picture' in request.FILES:
                        user.profile_picture = request.FILES['profile_picture']
                        user.save(update_fields=['profile_picture'])
                        logger.info(f"Profile picture saved directly: {user.profile_picture.name}")
                
                # Generate tokens for automatic login
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Registration successful',
                    'user': user_serializer.data,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error during user registration: {str(e)}")
                return Response({
                    'message': f'Registration failed: {str(e)}',
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            logger.error(f"Validation errors: {user_serializer.errors}")
            
            # Format error messages to be more user-friendly
            formatted_errors = {}
            if 'username' in user_serializer.errors:
                if 'unique' in str(user_serializer.errors['username']).lower():
                    formatted_errors['username'] = ['This username is already taken. Please choose another one.']
                else:
                    formatted_errors['username'] = user_serializer.errors['username']
            
            if 'email' in user_serializer.errors:
                if 'unique' in str(user_serializer.errors['email']).lower():
                    formatted_errors['email'] = ['This email address is already registered. Please use another one or try logging in.']
                else:
                    formatted_errors['email'] = user_serializer.errors['email']
                    
            # Include any other errors
            for field, errors in user_serializer.errors.items():
                if field not in formatted_errors:
                    formatted_errors[field] = errors
            
            return Response(formatted_errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error in register_user: {str(e)}")
        return Response({
            'message': f'Registration failed due to server error: {str(e)}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    username_or_email = request.data.get('usernameOrEmail') or request.data.get('username')
    password = request.data.get('password')
    
    if not username_or_email or not password:
        return Response({
            'error': 'Both username/email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Try to authenticate with username
    user = authenticate(username=username_or_email, password=password)
    
    # If authentication with username fails, try with email
    if not user:
        try:
            user_obj = UserProfile.objects.get(email=username_or_email)
            user = authenticate(username=user_obj.username, password=password)
        except UserProfile.DoesNotExist:
            pass
    
    if user:
        refresh = RefreshToken.for_user(user)
        
        # Check if user has preferences set
        has_preferences = False
        try:
            preferences = UserPreferences.objects.get(user=user)
            has_preferences = bool(preferences.travel_frequency and preferences.travel_budget)
        except UserPreferences.DoesNotExist:
            has_preferences = False
        
        return Response({
            'message': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserProfileSerializer(user).data,
            'has_preferences': has_preferences
        })
    else:
        # Check if user exists with the given username/email
        try:
            if '@' in username_or_email:
                user_exists = UserProfile.objects.filter(email=username_or_email).exists()
                if user_exists:
                    return Response({
                        'error': 'Incorrect password. Please try again.'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({
                        'error': 'No account found with this email address.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                user_exists = UserProfile.objects.filter(username=username_or_email).exists()
                if user_exists:
                    return Response({
                        'error': 'Incorrect password. Please try again.'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({
                        'error': 'No account found with this username.'
                    }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in login validation: {str(e)}")
            return Response({
                'error': 'Invalid credentials. Please check your username/email and password.'
            }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    try:
        user = request.user
        if request.method == 'GET':
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            # Create a mutable copy of the request data
            profile_data = request.data.copy() if hasattr(request.data, 'copy') else {k: v for k, v in request.data.items()}
            
            # Handle profile picture separately
            if 'profile_picture' in request.FILES:
                # Directly assign the file to the user model
                user.profile_picture = request.FILES['profile_picture']
                user.save(update_fields=['profile_picture'])
            
            # Remove profile_picture from data to avoid validation errors
            if 'profile_picture' in profile_data:
                del profile_data['profile_picture']
                
            # Log the profile data being updated
            logger.info(f"Updating profile for user {user.username} with data: {profile_data}")
            
            serializer = UserProfileSerializer(user, data=profile_data, partial=True)
            if serializer.is_valid():
                user = serializer.save()
                logger.info(f"Profile updated successfully for user {user.username}")
                
                # Log the updated phone number if it was changed
                if 'phone_number' in profile_data:
                    logger.info(f"Phone number updated to: {user.phone_number}")
                    
                return Response({
                    'message': 'Profile updated successfully',
                    'user': UserProfileSerializer(user).data
                })
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

# Helper functions for compatibility scoring
def calculate_date_overlap_score(trip1, trip2):
    """
    Calculate date overlap score (30% weight)
    Returns a score between 0 and 100 based on date overlap
    """
    # Calculate overlap
    start_overlap = max(trip1.start_date, trip2.start_date)
    end_overlap = min(trip1.end_date, trip2.end_date)

    if start_overlap > end_overlap:
        return 0  # No overlap

    overlap_days = (end_overlap - start_overlap).days + 1
    total_days = min((trip1.end_date - trip1.start_date).days + 1, (trip2.end_date - trip2.start_date).days + 1)

    return (overlap_days / total_days) * 100

def calculate_activities_score(trip1, trip2):
    """
    Calculate shared activities score (50% weight)
    Returns a score between 0 and 100 based on shared activities
    """
    trip1_activities = set(trip1.activities.values_list('id', flat=True))
    trip2_activities = set(trip2.activities.values_list('id', flat=True))
    
    if not trip1_activities or not trip2_activities:
        return 0

    shared_activities = len(trip1_activities.intersection(trip2_activities))
    total_activities = len(trip1_activities)

    return (shared_activities / total_activities) * 100

def calculate_preferences_score(trip1, trip2):
    """
    Calculate user preferences score (20% weight)
    Returns a score between 0 and 100 based on matching preferences
    """
    score = 0
    
    # Get user preferences
    try:
        trip1_prefs = UserPreferences.objects.get(user=trip1.user)
        trip2_prefs = UserPreferences.objects.get(user=trip2.user)
        
        # Check travel frequency match
        if trip1_prefs.travel_frequency == trip2_prefs.travel_frequency:
            score += 10
            
        # Check travel budget match
        if trip1_prefs.travel_budget == trip2_prefs.travel_budget:
            score += 10
            
    except UserPreferences.DoesNotExist:
        pass

    return score

def calculate_compatibility_score(trip1, trip2):
    """
    Calculate compatibility score between two trips based on:
    1. Destination Match (Mandatory Filter)
    2. Date Overlap (30%)
    3. Shared Activities (50%)
    4. User Preference Match (20%)
    
    Args:
        trip1 (Trip): First trip object
        trip2 (Trip): Second trip object
        
    Returns:
        float: Compatibility score as a percentage (0-100)
    """
    # Mandatory destination match
    if trip1.destination_id != trip2.destination_id:
        return 0

    # Calculate individual scores
    date_score = calculate_date_overlap_score(trip1, trip2) * 0.3  # 30% weight
    activities_score = calculate_activities_score(trip1, trip2) * 0.5  # 50% weight
    preferences_score = calculate_preferences_score(trip1, trip2) * 0.2  # 20% weight

    # Calculate final score
    final_score = date_score + activities_score + preferences_score
    
    return round(final_score, 2)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_compatible_trips(request):
    """
    Get trips compatible with the user's trip preferences
    """
    try:
        # Get current user's trip details from request
        trip_data = request.data
        
        # Parse and validate input data
        destination_id = int(trip_data['destinationId'])
        start_date = parser.parse(trip_data['startDate'])
        end_date = parser.parse(trip_data['endDate'])
        
        # Get current user's trip
        current_trip = Trip.objects.get(
            user=request.user,
            destination_id=destination_id,
            start_date=start_date,
            end_date=end_date
        )

        # Get other trips that match the destination
        compatible_trips = Trip.objects.filter(
            destination_id=destination_id,
            user__is_discoverable=True
        ).exclude(
            user=request.user
        ).prefetch_related('activities')

        # Calculate compatibility scores
        results = []
        for trip in compatible_trips:
            score = calculate_compatibility_score(current_trip, trip)
            if score > 0:
                results.append({
                    'trip': trip,
                    'compatibility_score': score
                })

        # Sort by compatibility score (highest first)
        results.sort(key=lambda x: x['compatibility_score'], reverse=True)

        # Serialize the results
        serialized_results = CompatibleTripSerializer(
            [item['trip'] for item in results],
            many=True,
            context={'compatibility_scores': {int(item['trip'].id): item['compatibility_score'] for item in results}}
        ).data

        return Response(serialized_results)

    except Trip.DoesNotExist:
        return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({'error': 'Invalid input data'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in get_compatible_trips: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_trip(request):
    try:
        # Get the request data
        data = request.data
        
        # Validate required fields
        required_fields = ['destinationId', 'startDate', 'endDate', 'maxMembers']
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            return Response({
                'detail': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse and validate data
        try:
            destination_id = int(data['destinationId'])
            max_members = int(data['maxMembers'])
            start_date = parser.parse(data['startDate'])
            end_date = parser.parse(data['endDate'])
            activities = data.get('activities', [])
            description = data.get('description', '')
        except (ValueError, TypeError) as e:
            return Response({
                'detail': f'Invalid data format: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate max_members
        if max_members < 1:
            return Response({
                'detail': 'max_members must be at least 1'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get the user's profile
        user_profile = request.user
        
        # Validate destination exists
        try:
            destination = PreferredDestination.objects.get(id=destination_id)
        except PreferredDestination.DoesNotExist:
            return Response({
                'detail': 'Destination not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Validate activities exist and belong to this destination
        if activities:
            try:
                # Get all valid activity IDs for this destination
                destination_activities = DestinationTravelInterest.objects.filter(
                    destination=destination
                ).values_list('interest_id', flat=True)
                
                # Get all valid TravelInterest IDs
                valid_activities = TravelInterest.objects.filter(
                    id__in=[int(id) for id in activities if id is not None]
                ).values_list('id', flat=True)
                
                # Check if all selected activities are valid
                invalid_activities = []
                for activity_id in activities:
                    if activity_id is None:
                        continue
                    
                    try:
                        activity_id = int(activity_id)
                        if activity_id not in destination_activities:
                            invalid_activities.append(activity_id)
                        elif activity_id not in valid_activities:
                            invalid_activities.append(activity_id)
                    except (ValueError, TypeError):
                        invalid_activities.append(activity_id)
                
                if invalid_activities:
                    return Response({
                        'detail': f'Invalid activity IDs: {invalid_activities}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                logger.error(f"Error validating activities: {str(e)}")
                return Response({
                    'detail': f'Error validating activities: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create the trip
        try:
            trip = Trip.objects.create(
                user=user_profile,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                max_members=max_members,
                description=description,
                status='open'
            )
            
            # Add activities
            if activities:
                activity_objects = TravelInterest.objects.filter(id__in=activities)
                trip.activities.set(activity_objects)

            return Response({
                'detail': 'Trip created successfully',
                'trip_id': trip.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'detail': f'Error creating trip: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"Error in save_trip: {str(e)}")
        return Response({
            'detail': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Changed to require authentication
def check_trip_dates(request):
    try:
        # Parse dates from request
        start_date = datetime.fromisoformat(request.data.get('startDate').replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(request.data.get('endDate').replace('Z', '+00:00'))
        destination_id = request.data.get('destinationId')
        
        # Get the current user
        user = request.user
        
        # Log for debugging
        print(f'Checking date overlap for user {user.username}: {start_date} to {end_date}')
        print(f'Request data: {request.data}')
        print(f'User authenticated: {request.user.is_authenticated}')
        
        # Check for conflicts with trips created by the user
        user_created_conflicts = Trip.objects.filter(
            user=user,  # Only check trips created by this user
            start_date__lte=end_date,  # Trip starts before or on the end date
            end_date__gte=start_date  # Trip ends after or on the start date
        )
        
        # Check for conflicts with trips joined by the user
        user_joined_conflicts = Trip.objects.filter(
            members=user,  # Trips where user is a member
            start_date__lte=end_date,  # Trip starts before or on the end date
            end_date__gte=start_date  # Trip ends after or on the start date
        ).exclude(user=user)  # Exclude trips created by the user to avoid duplicates
        
        # Combine both sets of conflicts
        conflicts = user_created_conflicts | user_joined_conflicts
        
        # Log the conflicts found
        logger.info(f'Found {conflicts.count()} conflicting trips for user {user.username}')

        if conflicts.exists():
            # Generate suggested dates
            suggested_dates = []
            test_start = start_date
            for _ in range(3):  # Suggest 3 alternative date ranges
                test_start += timedelta(days=7)  # Try next week
                test_end = test_start + (end_date - start_date)  # Keep same duration
                
                # Check if suggested dates have conflicts
                has_conflict = Trip.objects.filter(
                    user=user,
                    start_date__lte=test_end,
                    end_date__gte=test_start
                ).exists() or Trip.objects.filter(
                    members=user,
                    start_date__lte=test_end,
                    end_date__gte=test_start
                ).exclude(user=user).exists()
                
                if not has_conflict:
                    suggested_dates.append({
                        'start': test_start.isoformat(),
                        'end': test_end.isoformat()
                    })

            return Response({
                'hasConflict': True,
                'suggestedDates': suggested_dates
            })

        return Response({'hasConflict': False})
        
    except Exception as e:
        logger.error(f'Error checking trip dates: {str(e)}')
        return Response({
            'hasConflict': False,
            'error': 'Failed to check date availability'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    try:
        preferences = UserPreferences.objects.get(user=request.user)
        serializer = UserPreferencesSerializer(preferences)
        return Response(serializer.data)
    except UserPreferences.DoesNotExist:
        return Response({
            'travel_frequency': None,
            'travel_budget': None
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def trips(request):
    try:
        trips = Trip.objects.all()
        
        # Use different serializer based on query parameter
        if request.query_params.get('serializer') == 'destination_details':
            serializer = TripDetailSerializer(trips, many=True)
        else:
            serializer = TripSerializer(trips, many=True)
        
        return Response(serializer.data)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_trips(request):
    try:
        # Get user ID from request parameters or use the authenticated user
        user_id = request.query_params.get('user_id')
        if user_id:
            user = get_object_or_404(UserProfile, id=user_id)
        else:
            user = request.user
            
        # Get all trips where user is either the creator or a member
        trips = Trip.objects.filter(
            Q(user=user) | Q(members=user)
        ).distinct()
        
        # Log for debugging
        logger.info(f"Fetching trips for user {user.username} (ID: {user.id})")
        logger.info(f"Found {trips.count()} trips")
        
        # Use different serializer based on query parameter
        if request.query_params.get('serializer') == 'destination_details':
            serializer = TripDetailSerializer(trips, many=True)
        else:
            serializer = TripSerializer(trips, many=True)
        
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error in user_trips: {str(e)}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_buddy_requests(request):
    try:
        # Get only requests sent to the user
        received_requests = TravelBuddyRequest.objects.filter(to_user=request.user)
        
        # Check if we need to filter for unread requests only
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        
        if unread_only:
            received_requests = received_requests.filter(status='pending')
            
        # Serialize and return the received requests
        serializer = TravelBuddyRequestSerializer(received_requests, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        logger.error(f"Error fetching buddy requests: {str(e)}")
        return Response(
            {'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_buddy_request(request):
    to_user_id = request.data.get('toUserId')
    trip_details = request.data.get('tripDetails')

    if not to_user_id or not trip_details:
        return Response({'error': 'Missing required data'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        to_user = UserProfile.objects.get(id=to_user_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Create or get trip
    trip, _ = Trip.objects.get_or_create(
        user=request.user,
        destination_id=trip_details['destinationId'],
        start_date=datetime.fromisoformat(trip_details['startDate'].replace('Z', '+00:00')),
        end_date=datetime.fromisoformat(trip_details['endDate'].replace('Z', '+00:00'))
    )

    # Check if request already exists
    existing_request = TravelBuddyRequest.objects.filter(
        from_user=request.user,
        to_user=to_user,
        trip=trip
    ).first()

    if existing_request:
        return Response({'error': 'Request already sent'}, status=status.HTTP_400_BAD_REQUEST)

    # Create buddy request
    buddy_request = TravelBuddyRequest.objects.create(
        from_user=request.user,
        to_user=to_user,
        trip=trip,
        status='pending'
    )

    return Response({
        'message': 'Buddy request sent successfully',
        'request': TravelBuddyRequestSerializer(buddy_request).data
    })

class HandleBuddyRequestView(generics.GenericAPIView):
    """
    Handle buddy request actions (accept/reject).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request_id = request.data.get('request_id')
        action = request.data.get('action')  # 'accept' or 'reject'

        try:
            buddy_request = get_object_or_404(
                TravelBuddyRequest,
                id=request_id,
                to_user=request.user,
                status='pending'
            )
        except TravelBuddyRequest.DoesNotExist:
            return Response(
                {'error': 'Request not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if action == 'accept':
            # Update the request status to accepted
            buddy_request.status = 'accepted'
            buddy_request.save()

            # Get the trip associated with this request
            trip = buddy_request.trip

            # Add both users to each other's buddy list for this trip
            # First, get or create the buddy request in the opposite direction
            reverse_request, created = TravelBuddyRequest.objects.get_or_create(
                from_user=request.user,
                to_user=buddy_request.from_user,
                trip=trip,
                defaults={'status': 'accepted'}
            )

            # If the reverse request was pending, update its status to accepted
            if not created and reverse_request.status == 'pending':
                reverse_request.status = 'accepted'
                reverse_request.save()

            return Response(
                {'message': 'Buddy request accepted'},
                status=status.HTTP_200_OK
            )
        elif action == 'reject':
            buddy_request.status = 'rejected'
            buddy_request.save()
            return Response(
                {'message': 'Buddy request rejected'},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Invalid action'},
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_preferences(request):
    try:
        user_profile = request.user
        preferences, created = UserPreferences.objects.get_or_create(user=user_profile)
        
        preferences.travel_frequency = request.data.get('travel_frequency')
        preferences.travel_budget = request.data.get('travel_budget')
        preferences.save()
        
        return Response({
            'message': 'Preferences updated successfully',
            'preferences': {
                'travel_frequency': preferences.travel_frequency,
                'travel_budget': preferences.travel_budget
            }
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@require_http_methods(["POST"])
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
            token = request.headers.get('Authorization', '').split(' ')[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                return JsonResponse({'detail': 'Invalid token'}, status=401)
            
            user = UserProfile.objects.get(id=user_id)
            
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            if not current_password or not new_password or not confirm_password:
                return JsonResponse({'detail': 'All fields are required'}, status=400)
            
            if new_password != confirm_password:
                return JsonResponse({'detail': 'New passwords do not match'}, status=400)
            
            if not user.check_password(current_password):
                return JsonResponse({'detail': 'Current password is incorrect'}, status=400)
            
            if len(new_password) < 8:
                return JsonResponse({'detail': 'Password must be at least 8 characters long'}, status=400)
            
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({'detail': 'Password changed successfully'})
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'detail': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'detail': 'Invalid token'}, status=401)
        except UserProfile.DoesNotExist:
            return JsonResponse({'detail': 'User not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'detail': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def find_travel_buddies(request):
    try:
        # Log request details
        logger.info(f"Received find_travel_buddies request")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Get and validate JWT token
        token = request.headers.get('Authorization', '').split(' ')[1]
        if not token:
            logger.warning("No authorization token provided")
            return JsonResponse({'detail': 'Authorization token required'}, status=401)
            
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                logger.warning("Invalid token - no user_id found")
                return JsonResponse({'detail': 'Invalid token'}, status=401)
            
            # Get the current user's trip details from the request body
            trip_details = json.loads(request.body)
            trip_id = trip_details.get('trip_id')
            destination = trip_details.get('destination')
            start_date = trip_details.get('start_date')
            end_date = trip_details.get('end_date')
            
            if not all([trip_id, destination, start_date, end_date]):
                logger.warning("Missing required trip details")
                return JsonResponse({'detail': 'Missing required trip details'}, status=400)
            
            try:
                # Log database query details
                logger.info(f"Fetching trip with ID: {trip_id}")
                logger.info(f"Fetching user with ID: {user_id}")
                
                # Get the current trip and user preferences
                current_trip = Trip.objects.get(id=trip_id)
                current_user = UserProfile.objects.get(id=user_id)
                
                logger.info(f"Found trip: {current_trip.destination.name} from {current_trip.start_date} to {current_trip.end_date}")
                logger.info(f"Found user: {current_user.username}")
                
                current_preferences = getattr(current_user, 'preferences', None)
                
                if current_preferences:
                    logger.info(f"User has preferences: budget={current_preferences.travel_budget}, frequency={current_preferences.travel_frequency}")
                else:
                    logger.info("User has no preferences set")
                
                # Helper function to check if two date ranges overlap
                def date_ranges_overlap(start1, end1, start2, end2):
                    return (start1 <= end2 and end1 >= start2)
                
                # Find other users with trips to the same destination
                # Exclude the current user and their current trip
                # Also exclude users who are already connected via accepted buddy requests
                logger.info(f"Searching for buddies with trips to {current_trip.destination.name}")
                
                # Get all users the current user is already connected with
                existing_buddies = TravelBuddyRequest.objects.filter(
                    Q(from_user=current_user) | Q(to_user=current_user),
                    status='accepted'
                ).values_list('from_user', 'to_user')
                
                # Get unique list of existing buddies
                existing_buddies_set = set()
                for from_user, to_user in existing_buddies:
                    existing_buddies_set.add(from_user)
                    existing_buddies_set.add(to_user)
                
                existing_buddies_set.discard(current_user.id)  # Remove current user if present
                logger.info(f"Found {len(existing_buddies_set)} existing buddies")
                
                buddies = UserProfile.objects.filter(
                    trips__destination=current_trip.destination,
                    is_discoverable=True  # Only show discoverable users
                ).exclude(
                    id__in=existing_buddies_set
                ).exclude(
                    id=user_id
                ).distinct()
                
                logger.info(f"Found {buddies.count()} potential buddies after filtering")
                
                # Filter buddies based on date overlap and shared activities
                buddies_with_overlap = []
                for buddy in buddies:
                    buddy_trips = buddy.trips.filter(
                        destination=current_trip.destination
                    )
                    
                    for buddy_trip in buddy_trips:
                        if date_ranges_overlap(
                            current_trip.start_date,
                            current_trip.end_date,
                            buddy_trip.start_date,
                            buddy_trip.end_date
                        ):
                            buddies_with_overlap.append(buddy)
                            break
                
                logger.info(f"Found {len(buddies_with_overlap)} buddies with date overlap")
                
                # Calculate compatibility scores and prepare flat response
                buddy_scores = []
                for buddy in buddies_with_overlap:
                    buddy_trip = buddy.trips.filter(
                        destination=current_trip.destination
                    ).first()
                    
                    if buddy_trip:
                        score = calculate_compatibility_score(current_trip, buddy_trip)
                        buddy_scores.append({
                            'id': buddy.id,
                            'username': buddy.username,
                            'profile_picture': request.build_absolute_uri(buddy.profile_picture.url) if buddy.profile_picture else None,
                            'gender': buddy.gender,
                            'compatibility_score': score
                        })
                
                # Sort buddies by compatibility score (highest first)
                buddy_scores.sort(key=lambda x: x['compatibility_score'], reverse=True)
                
                return JsonResponse({
                    'destination': current_trip.destination.name,
                    'buddies': buddy_scores
                })
                
            except Trip.DoesNotExist:
                logger.warning(f"Trip not found with ID: {trip_id}")
                return JsonResponse({'detail': 'Trip not found'}, status=404)
            except UserProfile.DoesNotExist:
                logger.warning(f"User not found with ID: {user_id}")
                return JsonResponse({'detail': 'User not found'}, status=404)
            except Exception as e:
                logger.error(f"Error processing trip data: {str(e)}")
                return JsonResponse({'detail': str(e)}, status=500)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return JsonResponse({'detail': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return JsonResponse({'detail': 'Invalid token'}, status=401)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON data in request body")
            return JsonResponse({'detail': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return JsonResponse({'detail': str(e)}, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in find_travel_buddies: {str(e)}")
        return JsonResponse({'detail': 'Internal server error'}, status=500)

# Helper function to check if user is already a member of a trip
def is_user_member(trip, user):
    return trip.members.filter(id=user.id).exists()

@permission_classes([IsAuthenticated])
class JoinTripView(APIView):
    def post(self, request, trip_id):
        try:
            # Get the trip
            trip = get_object_or_404(Trip, id=trip_id)

            # Check if user can join
            if not trip.can_join(request.user):
                if trip.is_full():
                    return Response({
                        'detail': 'This trip is full'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif trip.status == 'completed':
                    return Response({
                        'detail': 'This trip has already completed'
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'detail': 'You are already a member of this trip'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Add user to trip
            trip.members.add(request.user)
            
            # Create notifications for trip joining
            create_trip_join_notifications(trip, request.user)

            return Response({
                'detail': 'Successfully joined trip',
                'trip_id': trip.id
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error joining trip: {str(e)}")
            return Response({
                'detail': 'Failed to join trip'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class TripDetailsView(APIView):
    def get(self, request, trip_id):
        try:
            # Get the trip
            trip = get_object_or_404(Trip, id=trip_id)

            # Serialize the trip data
            serializer = TripDetailSerializer(trip)
            
            return Response(serializer.data)
            
        except Http404:
            return Response({
                'detail': 'Trip not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error fetching trip details: {str(e)}")
            return Response({
                'detail': 'Failed to fetch trip details'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class CompatibleTripsView(APIView):
    def get_travel_preferences(self, user):
        """
        Get formatted travel preferences for a user
        """
        try:
            prefs = UserPreferences.objects.get(user=user)
            preferences = []
            
            if prefs.travel_budget:
                budget_display = dict(UserPreferences.TRAVEL_BUDGET_CHOICES).get(prefs.travel_budget, prefs.travel_budget)
                preferences.append(budget_display)
                
            if prefs.travel_frequency:
                frequency_display = dict(UserPreferences.TRAVEL_FREQUENCY_CHOICES).get(prefs.travel_frequency, prefs.travel_frequency)
                preferences.append(frequency_display)
                
            if preferences:
                return ', '.join(preferences)
            return 'Not specified'
        except UserPreferences.DoesNotExist:
            return 'Not specified'
    
    def post(self, request):
        try:
            # Get user's profile
            user_profile = request.user
            
            # Get trip details from request
            destination_id = request.data.get('destinationId')
            activities = request.data.get('activities', [])
            start_date = datetime.fromisoformat(request.data.get('startDate').replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(request.data.get('endDate').replace('Z', '+00:00'))

            # Find compatible trips
            compatible_trips = Trip.objects.filter(
                destination_id=destination_id,
                status='open',
                start_date__range=[start_date - timedelta(days=2), start_date + timedelta(days=2)],
                end_date__range=[end_date - timedelta(days=2), end_date + timedelta(days=2)]
            ).exclude(
                user=user_profile
            ).annotate(
                shared_activities_count=Count('activities', filter=Q(activities__id__in=activities)),
                member_count=Count('members')
            ).filter(
                shared_activities_count__gt=0,
                member_count__lt=F('max_members')
            ).distinct()

            # Prepare response data
            trips_data = []
            
            # Get user preferences for compatibility scoring
            try:
                user_prefs = UserPreferences.objects.get(user=user_profile)
            except UserPreferences.DoesNotExist:
                user_prefs = None
                
            # Get the activity IDs from the request
            user_activity_ids = set(activities)
            
            # Process each compatible trip
            for trip in compatible_trips:
                # Calculate compatibility score directly without using the helper functions
                # 1. Date overlap (30% weight)
                date_score = 0
                if start_date and end_date and trip.start_date and trip.end_date:
                    # Make sure dates are timezone-aware for comparison
                    from django.utils import timezone
                    
                    # Convert user input dates to timezone-aware if they're naive
                    user_start_date = timezone.make_aware(start_date) if timezone.is_naive(start_date) else start_date
                    user_end_date = timezone.make_aware(end_date) if timezone.is_naive(end_date) else end_date
                    
                    # Get trip dates and ensure they're timezone-aware
                    trip_start_date = timezone.make_aware(trip.start_date) if timezone.is_naive(trip.start_date) else trip.start_date
                    trip_end_date = timezone.make_aware(trip.end_date) if timezone.is_naive(trip.end_date) else trip.end_date
                    
                    # Now compare the timezone-aware dates
                    start_overlap = max(user_start_date, trip_start_date)
                    end_overlap = min(user_end_date, trip_end_date)
                    
                    if start_overlap <= end_overlap:
                        overlap_days = (end_overlap - start_overlap).days + 1
                        total_days = min((user_end_date - user_start_date).days + 1, (trip_end_date - trip_start_date).days + 1)
                        if total_days > 0:
                            date_score = (overlap_days / total_days) * 100 * 0.3  # 30% weight
                
                # 2. Shared activities (50% weight)
                activities_score = 0
                trip_activity_ids = set(trip.activities.values_list('id', flat=True))
                
                if user_activity_ids and trip_activity_ids:
                    shared_activities = len(user_activity_ids.intersection(trip_activity_ids))
                    total_activities = len(user_activity_ids)
                    if total_activities > 0:
                        activities_score = (shared_activities / total_activities) * 100 * 0.5  # 50% weight
                
                # 3. User preferences (20% weight)
                preferences_score = 0
                if user_prefs:
                    try:
                        trip_prefs = UserPreferences.objects.get(user=trip.user)
                        
                        # Check travel frequency match
                        if user_prefs.travel_frequency == trip_prefs.travel_frequency:
                            preferences_score += 10
                            
                        # Check travel budget match
                        if user_prefs.travel_budget == trip_prefs.travel_budget:
                            preferences_score += 10
                            
                        preferences_score = preferences_score * 0.2  # 20% weight
                    except UserPreferences.DoesNotExist:
                        pass
                
                # Calculate final score
                compatibility_score = date_score + activities_score + preferences_score
                trip_data = {
                    'id': trip.id,
                    'destination': {
                        'id': trip.destination.id,
                        'name': trip.destination.name
                    },
                    'creator': {
                        'id': trip.user.id,
                        'username': trip.user.username,
                        'gender': trip.user.get_gender_display() if trip.user.gender else 'Not specified',
                        'travel_preferences': self.get_travel_preferences(trip.user),
                        'date_of_birth': trip.user.dob.isoformat() if trip.user.dob else None
                    },
                    'activities': [
                        {
                            'id': activity.id,
                            'name': activity.name
                        }
                        for activity in trip.activities.all()
                    ],
                    'start_date': trip.start_date.isoformat(),
                    'end_date': trip.end_date.isoformat(),
                    'max_members': trip.max_members,
                    'current_members': trip.member_count,
                    'status': trip.status,
                    'description': trip.description or '',
                    'can_join': not is_user_member(trip, user_profile),
                    'compatibility_score': round(compatibility_score, 2)
                }
                trips_data.append(trip_data)

            # Sort trips by compatibility score (highest first)
            trips_data.sort(key=lambda x: x['compatibility_score'], reverse=True)

            return JsonResponse(trips_data, safe=False)

        except Exception as e:
            logger.error(f"Error finding compatible trips: {str(e)}")
            return Response({
                'detail': 'Failed to find compatible trips'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MyTripsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get all trips where user is either the creator or a member
            trips = Trip.objects.filter(
                Q(user=request.user) | Q(members=request.user)
            ).distinct()
            
            # Log the number of trips found, including cancelled ones
            cancelled_trips = trips.filter(status='cancelled')
            logger.info(f'Found {trips.count()} total trips for user {request.user.username}, including {cancelled_trips.count()} cancelled trips')
            
            # Log each cancelled trip for debugging
            for trip in cancelled_trips:
                logger.info(f'Cancelled trip found: ID={trip.id}, Destination={trip.destination.name}, Status={trip.status}, Cancelled by={trip.cancelled_by.username if trip.cancelled_by else "Unknown"}')

            # Serialize the trips
            serializer = TripSerializer(trips, many=True)
            
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error fetching my trips: {str(e)}")
            return Response({
                'detail': 'Failed to fetch your trips'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BuddyProfileView(APIView):
    def get(self, request, user_id):
        user = get_object_or_404(UserProfile, id=user_id)
        serializer = BuddyProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

class SendBuddyRequestView(APIView):
    def post(self, request, buddy_id):
        from_user = request.user
        to_user = get_object_or_404(UserProfile, id=buddy_id)
        trip_id = request.data.get('trip_id')
        
        if not trip_id:
            return Response(
                {'detail': 'Trip ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        trip = get_object_or_404(Trip, id=trip_id)
        
        if from_user == to_user:
            return Response(
                {'detail': 'Cannot send request to yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        existing_request = TravelBuddyRequest.objects.filter(
            from_user=from_user,
            to_user=to_user,
            trip=trip
        ).first()

        if existing_request:
            if existing_request.status == 'pending':
                return Response(
                    {'detail': 'Request already sent'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing_request.status == 'accepted':
                return Response(
                    {'detail': 'Already travel buddies'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        buddy_request = TravelBuddyRequest.objects.create(
            from_user=from_user,
            to_user=to_user,
            trip=trip,
            status='pending'
        )
        
        return Response(
            {'detail': 'Buddy request sent successfully'},
            status=status.HTTP_201_CREATED
        )

class MyBuddiesView(generics.ListAPIView):
    """View to list all trips and their confirmed buddies for the current user."""
    serializer_class = MyBuddiesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            # Get all trips where the user is involved (either as creator or buddy)
            user_trips = Trip.objects.filter(
                Q(user=user) |
                Q(buddy_requests__from_user=user, buddy_requests__status='accepted') |
                Q(buddy_requests__to_user=user, buddy_requests__status='accepted')
            ).distinct()
            
            # For each trip, get all confirmed buddies
            for trip in user_trips:
                # Get all accepted requests for this trip
                accepted_requests = TravelBuddyRequest.objects.filter(
                    trip=trip,
                    status='accepted'
                )
                
                # Get all unique users involved in these requests
                # This will include both request senders and recipients
                buddies = set()
                for request in accepted_requests:
                    if request.from_user != user:
                        buddies.add(request.from_user)
                    if request.to_user != user:
                        buddies.add(request.to_user)
                
                # Convert the set to a list and sort by username
                sorted_buddies = sorted(buddies, key=lambda x: x.username.lower())
                
                # Add the sorted buddies to the trip object
                setattr(trip, 'buddies', sorted_buddies)
                
                # Count the number of buddies
                setattr(trip, 'buddy_count', len(sorted_buddies))
            
            return user_trips
            
        except Exception as e:
            logger.error(f"Error in MyBuddiesView: {str(e)}")
            raise


class TripChatMessagesView(generics.ListCreateAPIView):
    """View to list and create chat messages for a specific trip."""
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        trip_id = self.kwargs.get('trip_id')
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Check if the user is a member of the trip
        if self.request.user not in trip.members.all() and self.request.user != trip.user:
            return ChatMessage.objects.none()
        
        return ChatMessage.objects.filter(trip_id=trip_id)
    
    def perform_create(self, serializer):
        trip_id = self.kwargs.get('trip_id')
        trip = get_object_or_404(Trip, id=trip_id)
        
        # Check if the user is a member of the trip
        if self.request.user not in trip.members.all() and self.request.user != trip.user:
            raise PermissionDenied("You must be a member of this trip to send messages.")
        
        # Save the chat message
        chat_message = serializer.save(sender=self.request.user, trip=trip)
        
        # Create chat notifications for all trip members except the sender
        self.create_chat_notifications(trip, chat_message)
        
    def create_chat_notifications(self, trip, chat_message):
        """Create chat notifications for all trip members except the sender."""
        sender = self.request.user
        
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
        for recipient in recipients:
            ChatNotification.objects.create(
                user=recipient,
                trip=trip,
                chat_message=chat_message,
                sender=sender,
                message_preview=message_preview,
                is_read=False
            )

class TripCreateView(APIView):
    """
    View to create a new trip with buddy limit enforcement.
    
    POST /api/trips/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Get and validate input data
            data = request.data
            
            # Required fields
            required_fields = ['destinationId', 'activities', 'startDate', 'endDate', 'maxMembers']
            if not all(field in data for field in required_fields):
                return JsonResponse({
                    'detail': f'Missing required fields: {set(required_fields) - set(data.keys())}'
                }, status=400)

            # Validate maxMembers
            try:
                max_members = int(data['maxMembers'])
                if max_members < 1:
                    return JsonResponse({
                        'detail': 'Number of members must be at least 1.'
                    }, status=400)
            except (ValueError, TypeError):
                return JsonResponse({
                    'detail': 'maxMembers must be a positive integer.'
                }, status=400)

            # Convert dates
            try:
                start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({
                    'detail': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)' 
                }, status=400)

            # Validate activities
            try:
                activities = [int(a) for a in data['activities']]
            except (ValueError, TypeError):
                return JsonResponse({
                    'detail': 'activities must be a list of integers.'
                }, status=400)

            # Get destination
            try:
                destination = PreferredDestination.objects.get(id=data['destinationId'])
            except PreferredDestination.DoesNotExist:
                return JsonResponse({
                    'detail': 'Destination not found.'
                }, status=404)

            # Get user's profile
            user_profile = request.user.userprofile

            # Create the trip
            trip = Trip.objects.create(
                user=user_profile,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                max_members=max_members,
                status='open',
                description=data.get('description', '')
            )

            # Add activities
            trip.activities.set(activities)

            # Return the created trip
            return JsonResponse({
                'trip': {
                    'id': trip.id,
                    'destination': trip.destination.name,
                    'start_date': trip.start_date.isoformat(),
                    'end_date': trip.end_date.isoformat(),
                    'max_members': trip.max_members,
                    'current_members': 0,  # Creator is not counted in members
                    'status': trip.status,
                    'description': trip.description
                },
                'message': 'Trip created successfully. Other users can now join.'
            }, status=201)

        except Exception as e:
            logger.error(f"Error in TripCreateView: {str(e)}")
            return JsonResponse({
                'detail': 'Internal server error'
            }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    
    # Get or create preferences
    preferences, created = UserPreferences.objects.get_or_create(user=user)
    
    # Get the full URL for the profile picture
    profile_picture_url = None
    if user.profile_picture and hasattr(user.profile_picture, 'url'):
        profile_picture_url = request.build_absolute_uri(user.profile_picture.url)
    
    profile_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'gender': user.gender,
        'dob': user.dob,
        'phone_number': user.phone_number,  # Add phone number to response
        'profile_picture': profile_picture_url,
        'preferences': {
            'travel_frequency': preferences.travel_frequency,
            'travel_budget': preferences.travel_budget
        }
    }
    
    # Log the phone number for debugging
    print(f'User phone number: {user.phone_number}')
    
    return Response(profile_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_travel_interests(request):
    try:
        interests = TravelInterest.objects.all()
        interests_data = []
        
        for interest in interests:
            interests_data.append({
                'id': interest.id,
                'name': interest.name,
                'description': interest.description,
                'image': request.build_absolute_uri(interest.image.url) if interest.image else None,
                'created_at': interest.created_at.isoformat(),
                'updated_at': interest.updated_at.isoformat()
            })
        
        return Response(interests_data)
    except Exception as e:
        logger.error(f"Error fetching travel interests: {str(e)}")
        return Response({
            'detail': 'Failed to fetch travel interests'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def join_trip(request, trip_id):
    try:
        trip = Trip.objects.get(id=trip_id)
        
        # Check if trip is full
        if trip.is_full():
            return JsonResponse({
                'detail': 'This trip is full'
            }, status=400)
            
        # Check if user is already a member
        if trip.members.filter(id=request.user.id).exists():
            return JsonResponse({
                'detail': 'You are already a member of this trip'
            }, status=400)
            
        # Add user to members
        trip.members.add(request.user)
        trip.save()
        
        return JsonResponse({
            'detail': 'Successfully joined trip'
        })
        
    except Trip.DoesNotExist:
        return JsonResponse({
            'detail': 'Trip not found'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error joining trip: {str(e)}")
        return JsonResponse({
            'detail': 'Failed to join trip'
        }, status=500)

@api_view(['GET'])
def profile(request):
    try:
        # Get the user's profile
        user_profile = request.user
        
        # Get unread count if requested
        include_unread = request.GET.get('include_unread_count', 'false').lower() == 'true'
        include_phone = request.GET.get('include_phone', 'false').lower() == 'true'
        unread_count = 0
        
        if include_unread:
            # Count unread buddy requests
            unread_count = TravelBuddyRequest.objects.filter(
                to_user=user_profile,
                status='pending'
            ).count()
        
        # Serialize the profile
        serializer = UserProfileSerializer(user_profile)
        
        # Add the unread count to the response
        response_data = serializer.data
        
        # Ensure phone number is explicitly included in response
        logger.info(f"User profile data: {response_data}")
        logger.info(f"Phone number in profile: {user_profile.phone_number}")
        
        # Always include phone number in response
        response_data['phone_number'] = user_profile.phone_number
        
        if include_unread:
            response_data['unread_count'] = unread_count
        
        return Response(response_data)
    except Exception as e:
        logger.error(f"Error in profile view: {str(e)}")
        return Response({
            'detail': 'Failed to fetch profile'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDashboardView(APIView):
    """
    View to provide all data needed for the user dashboard, including:
    - Created trips
    - Joined trips
    - Trip statistics
    """
    def get(self, request):
        try:
            user = request.user
            
            # Get all trips where the user is either the creator or a member
            created_trips = Trip.objects.filter(user=user)
            
            # Get trips where user is a member but not the creator
            joined_trips = Trip.objects.filter(members=user).exclude(user=user)
            
            # Calculate trip status based on dates
            today = timezone.now().date()
            
            # Process created trips
            created_trips_data = []
            for trip in created_trips:
                # Determine status
                if trip.start_date > today:
                    status = 'Upcoming'
                elif trip.start_date <= today and trip.end_date >= today:
                    status = 'Ongoing'
                else:
                    status = 'Completed'
                    
                created_trips_data.append({
                    'id': trip.id,
                    'trip_name': trip.destination.name,
                    'destination': {
                        'name': trip.destination.name,
                        'location': trip.destination.location,
                        'image': request.build_absolute_uri(trip.destination.image.url) if trip.destination.image else None
                    },
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'status': status,
                    'members_count': trip.members.count(),
                    'max_members': trip.max_members
                })
            
            # Process joined trips
            joined_trips_data = []
            for trip in joined_trips:
                # Determine status
                if trip.start_date > today:
                    status = 'Upcoming'
                elif trip.start_date <= today and trip.end_date >= today:
                    status = 'Ongoing'
                else:
                    status = 'Completed'
                    
                joined_trips_data.append({
                    'id': trip.id,
                    'trip_name': trip.destination.name,
                    'creator': trip.user.username,
                    'destination': {
                        'name': trip.destination.name,
                        'location': trip.destination.location,
                        'image': request.build_absolute_uri(trip.destination.image.url) if trip.destination.image else None
                    },
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'status': status,
                    'members_count': trip.members.count(),
                    'max_members': trip.max_members
                })
            
            # Calculate stats
            stats = {
                'trips_created': created_trips.count(),
                'trips_joined': joined_trips.count(),
                'buddies_connected': self._calculate_unique_buddies(user, list(created_trips) + list(joined_trips))
            }
            
            return Response({
                'created_trips': created_trips_data,
                'joined_trips': joined_trips_data,
                'stats': stats
            })
            
        except Exception as e:
            logger.error(f"Error in user dashboard view: {str(e)}")
            return Response({
                'detail': 'Failed to fetch dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_unique_buddies(self, user, trips):
        # Calculate unique buddies from trips
        unique_buddy_ids = set()
        
        for trip in trips:
            for member in trip.members.all():
                if member.id != user.id:
                    unique_buddy_ids.add(member.id)
        
        return len(unique_buddy_ids)

class UserStatsView(APIView):
    """
    View to calculate and return the number of trips created, trips joined, and buddies connected
    for the currently logged-in user.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Count trips created by the user
            trips_created = Trip.objects.filter(user=user).count()
            
            # Count trips joined by the user (excluding trips created by the user)
            trips_joined = Trip.objects.filter(
                members=user
            ).exclude(
                user=user
            ).distinct().count()
            
            # Find unique buddies connected with the user
            # A buddy is defined as any other user who has joined the same trip(s) as the current user
            
            # First, get all trips where the user is either a creator or a member
            user_trips = Trip.objects.filter(
                Q(user=user) | Q(members=user)
            ).distinct()
            
            # Then, find all members of these trips (excluding the user themselves)
            buddies = UserProfile.objects.filter(
                Q(trips__in=user_trips) | Q(joined_trips__in=user_trips)
            ).exclude(
                id=user.id
            ).distinct()
            
            buddies_count = buddies.count()
            
            # Log for debugging
            logger.info(f"User stats for {user.username}: created={trips_created}, joined={trips_joined}, buddies={buddies_count}")
            
            # Return the stats as a JSON response
            return Response({
                'trips_created': trips_created,
                'trips_joined': trips_joined,
                'buddies_connected': buddies_count
            })
            
        except Exception as e:
            logger.error(f"Error in UserStatsView: {str(e)}")
            return Response({
                'detail': 'Failed to fetch user stats'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDashboardView(APIView):
    """
    View to return trip data for the user dashboard.
    Returns trips created and joined by the user with their status.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            today = timezone.now()
            
            # Get trips created by the user
            created_trips = Trip.objects.filter(user=user)
            
            # Get trips joined by the user (excluding trips created by the user)
            joined_trips = Trip.objects.filter(
                members=user
            ).exclude(
                user=user
            ).distinct()
            
            # Format created trips data
            created_trips_data = []
            for trip in created_trips:
                # Determine trip status based on dates
                if trip.start_date > today:
                    trip_status = 'Upcoming'
                elif trip.start_date <= today <= trip.end_date:
                    trip_status = 'Ongoing'
                else:  # trip.end_date < today
                    trip_status = 'Completed'
                
                # Get image URL
                image_url = None
                if trip.destination.image:
                    image_url = request.build_absolute_uri(trip.destination.image.url)
                else:
                    # Default image if none exists
                    image_url = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?q=80&w=300'
                
                created_trips_data.append({
                    'id': trip.id,
                    'trip_name': trip.destination.name,  # Using destination name as trip name
                    'image_url': image_url,
                    'status': trip_status,
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'destination': trip.destination.name,
                    'location': trip.destination.location,
                    'members_count': trip.members.count(),
                    'max_members': trip.max_members
                })
            
            # Format joined trips data
            joined_trips_data = []
            for trip in joined_trips:
                # Determine trip status based on dates
                if trip.start_date > today:
                    trip_status = 'Upcoming'
                elif trip.start_date <= today <= trip.end_date:
                    trip_status = 'Ongoing'
                else:  # trip.end_date < today
                    trip_status = 'Completed'
                
                # Get image URL
                image_url = None
                if trip.destination.image:
                    image_url = request.build_absolute_uri(trip.destination.image.url)
                else:
                    # Default image if none exists
                    image_url = 'https://images.unsplash.com/photo-1488646953014-85cb44e25828?q=80&w=300'
                
                joined_trips_data.append({
                    'id': trip.id,
                    'trip_name': trip.destination.name,  # Using destination name as trip name
                    'image_url': image_url,
                    'status': trip_status,
                    'start_date': trip.start_date,
                    'end_date': trip.end_date,
                    'destination': trip.destination.name,
                    'location': trip.destination.location,
                    'members_count': trip.members.count(),
                    'max_members': trip.max_members,
                    'creator': trip.user.username
                })
            
            # Log for debugging
            logger.info(f"User dashboard data for {user.username}: created={len(created_trips_data)}, joined={len(joined_trips_data)}")
            
            # Return the formatted data as a JSON response
            return Response({
                'created_trips': created_trips_data,
                'joined_trips': joined_trips_data
            })
            
        except Exception as e:
            logger.error(f"Error in UserDashboardView: {str(e)}")
            return Response({
                'detail': 'Failed to fetch dashboard data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import permission_classes
from django.utils import timezone

# Admin views
class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))

class AdminStatsView(APIView):
    """
    View to provide statistics for the admin dashboard.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            # Count various entities for dashboard stats
            users_count = UserProfile.objects.count()
            destinations_count = PreferredDestination.objects.count()
            interests_count = TravelInterest.objects.count()
            mappings_count = DestinationTravelInterest.objects.count()
            trips_count = Trip.objects.count()
            reviews_count = TripReview.objects.count()
            
            stats = {
                'users': users_count,
                'destinations': destinations_count,
                'interests': interests_count,
                'mappings': mappings_count,
                'trips': trips_count,
                'reviews': reviews_count
            }
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminUserListView(APIView):
    """
    View to list all users and create a new user.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        users = UserProfile.objects.all()
        user_data = []
        
        for user in users:
            # Count created and joined trips
            created_trips_count = Trip.objects.filter(user=user).count()
            joined_trips_count = user.joined_trips.count()
            
            # Get gender display value
            gender_display = user.get_gender_display() if user.gender else 'Not specified'
            
            # Calculate age if date of birth is available
            age = None
            if user.dob:
                today = timezone.now().date()
                age = today.year - user.dob.year - ((today.month, today.day) < (user.dob.month, user.dob.day))
            
            # Get serialized data and add additional fields
            user_data_dict = UserProfileSerializer(user).data
            user_data_dict['gender_display'] = gender_display
            user_data_dict['age'] = age
            user_data_dict['created_trips_count'] = created_trips_count
            user_data_dict['joined_trips_count'] = joined_trips_count
            
            user_data.append(user_data_dict)
        
        return Response(user_data)
    
    def post(self, request):
        try:
            # Log the incoming data for debugging
            print(f'Received user creation data: {request.data}')
            
            # Extract the required fields
            username = request.data.get('username')
            email = request.data.get('email')
            password = request.data.get('password')
            full_name = request.data.get('full_name', '')
            gender = request.data.get('gender', '')
            phone_number = request.data.get('phone_number', '')
            is_staff = request.data.get('is_staff', False)
            
            # Validate required fields
            if not username:
                return Response({'error': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not email:
                return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not password:
                return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user with this username already exists
            if UserProfile.objects.filter(username=username).exists():
                return Response({'error': 'A user with this username already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user with this email already exists
            if UserProfile.objects.filter(email=email).exists():
                return Response({'error': 'A user with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the user directly
            user = UserProfile.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Set additional fields
            user.full_name = full_name
            user.gender = gender
            user.phone_number = phone_number
            user.is_staff = is_staff
            user.save()
            
            # Return the serialized user data
            return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Log the exception for debugging
            import traceback
            print(f'Exception in user creation: {str(e)}')
            print(traceback.format_exc())
            return Response({
                'error': f'User creation failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

class AdminUserDetailView(APIView):
    """
    View to retrieve, update or delete a user instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return UserProfile.objects.get(pk=pk)
        except UserProfile.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        user = self.get_object(pk)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
    
    def put(self, request, pk):
        user = self.get_object(pk)
        data = request.data.copy()
        
        # Handle password separately if provided
        password = data.pop('password', None)
        
        serializer = UserProfileSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            # Save the user without password update first
            serializer.save()
            
            # Update password if provided
            if password and password.strip():
                user.set_password(password)
                user.save()
                
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminDestinationListView(APIView):
    """
    View to list all destinations and create a new destination.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        destinations = PreferredDestination.objects.all()
        serializer = PreferredDestinationSerializer(destinations, many=True, context={'request': request})
        data = serializer.data
        # Ensure all image URLs are absolute
        for destination in data:
            if destination.get('image') and not destination['image'].startswith('http'):
                destination['image'] = request.build_absolute_uri(destination['image'])
        return Response(data)
    
    def post(self, request):
        serializer = PreferredDestinationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminDestinationDetailView(APIView):
    """
    View to retrieve, update or delete a destination instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return PreferredDestination.objects.get(pk=pk)
        except PreferredDestination.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        destination = self.get_object(pk)
        serializer = PreferredDestinationSerializer(destination, context={'request': request})
        data = serializer.data
        # Ensure image URL is absolute
        if data.get('image') and not data['image'].startswith('http'):
            data['image'] = request.build_absolute_uri(data['image'])
        return Response(data)
    
    def put(self, request, pk):
        destination = self.get_object(pk)
        serializer = PreferredDestinationSerializer(destination, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        destination = self.get_object(pk)
        destination.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminDestinationInterestsView(APIView):
    """
    View to retrieve and update travel interests for a specific destination.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_destination(self, pk):
        try:
            return PreferredDestination.objects.get(pk=pk)
        except PreferredDestination.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        destination = self.get_destination(pk)
        # Get all travel interests associated with this destination
        destination_interests = DestinationTravelInterest.objects.filter(destination=destination)
        interests = [di.interest for di in destination_interests]
        serializer = TravelInterestSerializer(interests, many=True)
        return Response(serializer.data)
    
    def post(self, request, pk):
        destination = self.get_destination(pk)
        interest_ids = request.data.get('interests', [])
        
        # Clear existing interests
        DestinationTravelInterest.objects.filter(destination=destination).delete()
        
        # Add new interests
        for interest_id in interest_ids:
            try:
                interest = TravelInterest.objects.get(id=interest_id)
                DestinationTravelInterest.objects.create(
                    destination=destination,
                    interest=interest
                )
            except TravelInterest.DoesNotExist:
                pass  # Skip invalid interest IDs
        
        # Return updated interests
        destination_interests = DestinationTravelInterest.objects.filter(destination=destination)
        interests = [di.interest for di in destination_interests]
        serializer = TravelInterestSerializer(interests, many=True)
        return Response(serializer.data)

class AdminInterestListView(APIView):
    """
    View to list all travel interests and create a new interest.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        interests = TravelInterest.objects.all()
        serializer = TravelInterestSerializer(interests, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        serializer = TravelInterestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminInterestDetailView(APIView):
    """
    View to retrieve, update or delete a travel interest instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return TravelInterest.objects.get(pk=pk)
        except TravelInterest.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        interest = self.get_object(pk)
        serializer = TravelInterestSerializer(interest, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        interest = self.get_object(pk)
        serializer = TravelInterestSerializer(interest, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        interest = self.get_object(pk)
        interest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminDestinationInterestListView(APIView):
    """
    View to list all destination-interest mappings and create a new mapping.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        mappings = DestinationTravelInterest.objects.all()
        # Create a custom serializer or adapt an existing one for this purpose
        data = []
        for mapping in mappings:
            data.append({
                'id': mapping.id,
                'destination': {
                    'id': mapping.destination.id,
                    'name': mapping.destination.name
                },
                'interest': {
                    'id': mapping.interest.id,
                    'name': mapping.interest.name
                },
                'description': mapping.description,
                'created_at': mapping.created_at,
                'updated_at': mapping.updated_at
            })
        return Response(data)
    
    def post(self, request):
        try:
            destination_id = request.data.get('destination')
            interest_id = request.data.get('interest')
            description = request.data.get('description', '')
            
            destination = PreferredDestination.objects.get(id=destination_id)
            interest = TravelInterest.objects.get(id=interest_id)
            
            mapping = DestinationTravelInterest.objects.create(
                destination=destination,
                interest=interest,
                description=description
            )
            
            return Response({
                'id': mapping.id,
                'destination': {
                    'id': mapping.destination.id,
                    'name': mapping.destination.name
                },
                'interest': {
                    'id': mapping.interest.id,
                    'name': mapping.interest.name
                },
                'description': mapping.description,
                'created_at': mapping.created_at,
                'updated_at': mapping.updated_at
            }, status=status.HTTP_201_CREATED)
        except PreferredDestination.DoesNotExist:
            return Response({'error': 'Destination not found'}, status=status.HTTP_404_NOT_FOUND)
        except TravelInterest.DoesNotExist:
            return Response({'error': 'Interest not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminDestinationInterestDetailView(APIView):
    """
    View to retrieve, update or delete a destination-interest mapping instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return DestinationTravelInterest.objects.get(pk=pk)
        except DestinationTravelInterest.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        mapping = self.get_object(pk)
        return Response({
            'id': mapping.id,
            'destination': {
                'id': mapping.destination.id,
                'name': mapping.destination.name
            },
            'interest': {
                'id': mapping.interest.id,
                'name': mapping.interest.name
            },
            'description': mapping.description,
            'created_at': mapping.created_at,
            'updated_at': mapping.updated_at
        })
    
    def put(self, request, pk):
        mapping = self.get_object(pk)
        try:
            destination_id = request.data.get('destination')
            interest_id = request.data.get('interest')
            description = request.data.get('description', '')
            
            if destination_id:
                destination = PreferredDestination.objects.get(id=destination_id)
                mapping.destination = destination
            
            if interest_id:
                interest = TravelInterest.objects.get(id=interest_id)
                mapping.interest = interest
            
            mapping.description = description
            mapping.save()
            
            return Response({
                'id': mapping.id,
                'destination': {
                    'id': mapping.destination.id,
                    'name': mapping.destination.name
                },
                'interest': {
                    'id': mapping.interest.id,
                    'name': mapping.interest.name
                },
                'description': mapping.description,
                'created_at': mapping.created_at,
                'updated_at': mapping.updated_at
            })
        except PreferredDestination.DoesNotExist:
            return Response({'error': 'Destination not found'}, status=status.HTTP_404_NOT_FOUND)
        except TravelInterest.DoesNotExist:
            return Response({'error': 'Interest not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        mapping = self.get_object(pk)
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminTripListView(APIView):
    """
    View to list all trips and create a new trip.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        trips = Trip.objects.all()
        data = []
        for trip in trips:
            trip_data = {
                'id': trip.id,
                'user': {
                    'id': trip.user.id,
                    'username': trip.user.username
                },
                'destination': {
                    'id': trip.destination.id,
                    'name': trip.destination.name
                },
                'start_date': trip.start_date,
                'end_date': trip.end_date,
                'max_members': trip.max_members,
                'members_count': trip.members.count(),
                'status': trip.status,
                'description': trip.description,
                'created_at': trip.created_at,
                'is_cancelled': trip.is_cancelled
            }
            
            # Add cancellation information if the trip is cancelled
            if trip.status == 'cancelled' or trip.is_cancelled:
                trip_data['cancelled_by'] = {
                    'id': trip.cancelled_by.id,
                    'username': trip.cancelled_by.username
                } if trip.cancelled_by else None
                trip_data['cancelled_at'] = trip.cancelled_at
            
            data.append(trip_data)
        return Response(data)
    
    def post(self, request):
        try:
            user_id = request.data.get('user')
            destination_id = request.data.get('destination')
            start_date = request.data.get('start_date')
            end_date = request.data.get('end_date')
            max_members = request.data.get('max_members', 4)
            status_val = request.data.get('status', 'open')
            description = request.data.get('description', '')
            activities_ids = request.data.get('activities', [])
            
            user = UserProfile.objects.get(id=user_id)
            destination = PreferredDestination.objects.get(id=destination_id)
            
            trip = Trip.objects.create(
                user=user,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                max_members=max_members,
                status=status_val,
                description=description
            )
            
            # Add the creator as a member
            trip.members.add(user)
            
            # Add activities
            if activities_ids:
                activities = TravelInterest.objects.filter(id__in=activities_ids)
                trip.activities.set(activities)
            
            return Response({
                'id': trip.id,
                'user': {
                    'id': trip.user.id,
                    'username': trip.user.username
                },
                'destination': {
                    'id': trip.destination.id,
                    'name': trip.destination.name
                },
                'start_date': trip.start_date,
                'end_date': trip.end_date,
                'max_members': trip.max_members,
                'members_count': trip.members.count(),
                'status': trip.status,
                'description': trip.description,
                'created_at': trip.created_at
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminTripDetailView(APIView):
    """
    View to retrieve, update or delete a trip instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return Trip.objects.get(pk=pk)
        except Trip.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        trip = self.get_object(pk)
        data = {
            'id': trip.id,
            'user': {
                'id': trip.user.id,
                'username': trip.user.username
            },
            'destination': {
                'id': trip.destination.id,
                'name': trip.destination.name
            },
            'start_date': trip.start_date,
            'end_date': trip.end_date,
            'max_members': trip.max_members,
            'members_count': trip.members.count(),
            'status': trip.status,
            'description': trip.description,
            'created_at': trip.created_at,
            'is_cancelled': trip.is_cancelled,
            'activities': [
                {'id': activity.id, 'name': activity.name}
                for activity in trip.activities.all()
            ]
        }
        
        # Add cancellation information if the trip is cancelled
        if trip.status == 'cancelled' or trip.is_cancelled:
            data['cancelled_by'] = {
                'id': trip.cancelled_by.id,
                'username': trip.cancelled_by.username
            } if trip.cancelled_by else None
            data['cancelled_at'] = trip.cancelled_at
        return Response(data)
    
    def put(self, request, pk):
        trip = self.get_object(pk)
        try:
            # Update basic fields
            if 'user' in request.data:
                trip.user = UserProfile.objects.get(id=request.data['user'])
            if 'destination' in request.data:
                trip.destination = PreferredDestination.objects.get(id=request.data['destination'])
            if 'start_date' in request.data:
                trip.start_date = request.data['start_date']
            if 'end_date' in request.data:
                trip.end_date = request.data['end_date']
            if 'max_members' in request.data:
                trip.max_members = request.data['max_members']
            if 'status' in request.data:
                trip.status = request.data['status']
            if 'description' in request.data:
                trip.description = request.data['description']
            
            # Update activities
            if 'activities' in request.data:
                activities = TravelInterest.objects.filter(id__in=request.data['activities'])
                trip.activities.set(activities)
            
            trip.save()
            
            data = {
                'id': trip.id,
                'user': {
                    'id': trip.user.id,
                    'username': trip.user.username
                },
                'destination': {
                    'id': trip.destination.id,
                    'name': trip.destination.name
                },
                'start_date': trip.start_date,
                'end_date': trip.end_date,
                'max_members': trip.max_members,
                'members_count': trip.members.count(),
                'status': trip.status,
                'description': trip.description,
                'created_at': trip.created_at,
                'activities': [
                    {'id': activity.id, 'name': activity.name}
                    for activity in trip.activities.all()
                ]
            }
            return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        trip = self.get_object(pk)
        trip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminReviewListView(APIView):
    """
    View to list all reviews and create a new review.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        reviews = TripReview.objects.all().order_by('-created_at')
        serializer = TripReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        try:
            user_id = request.data.get('user')
            trip_id = request.data.get('trip')
            rating = request.data.get('rating')
            comment = request.data.get('comment', '')
            
            # Validate required fields
            if not user_id:
                return Response({'error': 'User is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not trip_id:
                return Response({'error': 'Trip is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not rating:
                return Response({'error': 'Rating is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user and trip objects
            user = UserProfile.objects.get(id=user_id)
            trip = Trip.objects.get(id=trip_id)
            
            # Check if a review already exists for this user and trip
            existing_review = TripReview.objects.filter(user=user, trip=trip).first()
            if existing_review:
                return Response({
                    'error': 'A review already exists for this user and trip'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the review
            review = TripReview.objects.create(
                user=user,
                trip=trip,
                rating=rating,
                comment=comment
            )
            
            serializer = TripReviewSerializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except UserProfile.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Trip.DoesNotExist:
            return Response({'error': 'Trip not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminReviewDetailView(APIView):
    """
    View to retrieve, update or delete a review instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return TripReview.objects.get(pk=pk)
        except TripReview.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        review = self.get_object(pk)
        serializer = TripReviewSerializer(review)
        return Response(serializer.data)
    
    def put(self, request, pk):
        review = self.get_object(pk)
        try:
            # Update fields if provided
            if 'rating' in request.data:
                review.rating = request.data.get('rating')
            if 'comment' in request.data:
                review.comment = request.data.get('comment')
            
            review.save()
            serializer = TripReviewSerializer(review)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        review = self.get_object(pk)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminTripMembersView(APIView):
    """
    View to list all members of a specific trip.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id)
            members = trip.members.all()
            creator = trip.user
            
            # Include creator in the response
            all_users = [creator] + list(members)
            serializer = UserProfileSerializer(all_users, many=True)
            return Response(serializer.data)
        except Trip.DoesNotExist:
            return Response({
                'error': 'Trip not found'
            }, status=status.HTTP_404_NOT_FOUND)

class AdminReviewListView(APIView):
    """
    View to list all trip reviews.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        reviews = TripReview.objects.all().order_by('-created_at')
        data = []
        for review in reviews:
            data.append({
                'id': review.id,
                'user': {
                    'id': review.user.id,
                    'username': review.user.username
                },
                'trip': {
                    'id': review.trip.id,
                    'destination': {
                        'id': review.trip.destination.id,
                        'name': review.trip.destination.name
                    },
                    'start_date': review.trip.start_date,
                    'end_date': review.trip.end_date,
                    'status': review.trip.status
                },
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at
            })
        return Response(data)

class AdminReviewDetailView(APIView):
    """
    View to retrieve or delete a review instance.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_object(self, pk):
        try:
            return TripReview.objects.get(pk=pk)
        except TripReview.DoesNotExist:
            raise Http404
    
    def get(self, request, pk):
        review = self.get_object(pk)
        data = {
            'id': review.id,
            'user': {
                'id': review.user.id,
                'username': review.user.username
            },
            'trip': {
                'id': review.trip.id,
                'destination': {
                    'id': review.trip.destination.id,
                    'name': review.trip.destination.name
                },
                'start_date': review.trip.start_date,
                'end_date': review.trip.end_date,
                'status': review.trip.status
            },
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at
        }
        return Response(data)
    
    def delete(self, request, pk):
        review = self.get_object(pk)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
from datetime import datetime, timedelta

from .models import Trip, TripReview
from .serializers import TripReviewSerializer
from .razorpay_utils import create_order, verify_payment_signature, get_payment_details, RAZORPAY_KEY_ID

# Add a simple test view to verify routing
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    """
    Create a Razorpay order for premium subscription
    """
    try:
        # Get plan details from request
        plan = request.data.get('plan')
        if not plan or plan not in ['silver', 'gold']:
            return Response({
                'error': 'Invalid plan selected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set amount based on plan
        amount = 299900 if plan == 'gold' else 29900  # in paise (₹2999 or ₹299)
        
        # Create a unique receipt ID
        receipt = f"premium_{request.user.id}_{datetime.now().timestamp()}"
        
        # Get user details for the order
        user = request.user
        
        # Add notes for reference
        notes = {
            'plan': plan,
            'user_id': str(user.id),
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name or user.username,
            'phone_number': user.phone_number or ''
        }
        
        # Create Razorpay order
        order = create_order(amount, receipt=receipt, notes=notes)
        
        return Response({
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key_id': RAZORPAY_KEY_ID  # Public key ID
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment and activate premium features
    """
    try:
        # Get payment details from request
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        
        if not payment_id or not order_id or not signature:
            return Response({
                'error': 'Missing payment details'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify payment signature
        is_valid = verify_payment_signature(payment_id, order_id, signature)
        
        if not is_valid:
            return Response({
                'error': 'Invalid payment signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get payment details to confirm amount and status
        payment_details = get_payment_details(payment_id)
        
        if payment_details['status'] != 'captured':
            return Response({
                'error': 'Payment not completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get plan from order notes
        plan = payment_details.get('notes', {}).get('plan')
        
        if not plan or plan not in ['silver', 'gold']:
            return Response({
                'error': 'Invalid subscription plan'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update user's premium status
        user_profile = request.user
        
        # Create or update subscription in the database
        try:
            # Check if user already has an active subscription
            existing_subscription = Subscription.objects.filter(
                user=user_profile,
                is_active=True
            ).first()
            
            if existing_subscription:
                # Update existing subscription
                existing_subscription.plan = plan
                existing_subscription.start_date = timezone.now()
                existing_subscription.end_date = None  # Will be set in save() method
                existing_subscription.save()
                subscription = existing_subscription
            else:
                # Create new subscription
                subscription = Subscription(
                    user=user_profile,
                    plan=plan
                )
                subscription.save()
                
            return Response({
                'success': True,
                'message': f'Payment verified successfully! You are now subscribed to the {subscription.get_plan_display()}.',
                'payment_id': payment_id,
                'plan': plan,
                'subscription_id': subscription.id,
                'valid_until': subscription.end_date.isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as sub_error:
            return Response({
                'error': f'Error saving subscription: {str(sub_error)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_subscription(request):
    """
    Check if the user has an active premium subscription
    """
    try:
        # Get the current user
        user = request.user
        
        # Check if the user has an active subscription
        active_subscription = Subscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now()  # Subscription hasn't expired
        ).first()
        
        if active_subscription:
            return Response({
                'has_subscription': True,
                'plan': active_subscription.plan,
                'end_date': active_subscription.end_date.isoformat(),
                'days_remaining': (active_subscription.end_date - timezone.now()).days
            })
        else:
            return Response({
                'has_subscription': False
            })
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_review_endpoint(request):
    return Response({"message": "Review endpoint test successful"}, status=status.HTTP_200_OK)


class TripReviewView(APIView):
    """View to create and retrieve trip reviews."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all reviews for the user's trips
        user = request.user
        
        # Get reviews created by the user
        user_reviews = TripReview.objects.filter(user=user)
        
        # Get reviews for trips created by or joined by the user
        created_trips = Trip.objects.filter(user=user)
        joined_trips = Trip.objects.filter(members=user)
        all_trips = list(created_trips) + list(joined_trips)
        trip_ids = [trip.id for trip in all_trips]
        trip_reviews = TripReview.objects.filter(trip_id__in=trip_ids)
        
        # Combine and remove duplicates
        all_reviews = user_reviews | trip_reviews
        
        serializer = TripReviewSerializer(all_reviews, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = TripReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Check if the trip exists and is completed
            trip_id = request.data.get('trip')
            try:
                trip = Trip.objects.get(id=trip_id)
                
                # Check if the trip should be marked as completed based on end date
                current_date = timezone.now()
                if trip.end_date < current_date and trip.status != 'cancelled':
                    # Automatically update the trip status to completed if it's past the end date
                    trip.status = 'completed'
                    trip.save(update_fields=['status'])
                    print(f"Updated trip {trip.id} status to 'completed'" )
                
                # Now check if the trip is marked as completed
                if trip.status != 'completed':
                    return Response(
                        {"error": "Reviews can only be submitted for completed trips."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if the user is the creator or a member of the trip
                user = request.user
                if trip.user != user and user not in trip.members.all():
                    return Response(
                        {"error": "You can only review trips you created or joined."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Save the review
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Trip.DoesNotExist:
                return Response(
                    {"error": "Trip not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LatestReviewsView(APIView):
    """View to retrieve the latest reviews for the homepage."""
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get the latest 5 reviews - removed is_public filter since it doesn't exist
        latest_reviews = TripReview.objects.order_by('-created_at')[:5]
        serializer = TripReviewSerializer(latest_reviews, many=True)
        return Response(serializer.data)


class CancelTripView(APIView):
    """View to cancel a trip created by the user.
    
    Only the creator of the trip can cancel it, and it must be at least 3 days before the trip starts.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, trip_id):
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            
            # Check if the user is the creator of the trip
            if trip.creator != request.user:
                return Response({
                    'error': 'Only the creator of the trip can cancel it'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if the trip is already canceled
            if trip.status == 'cancelled':
                return Response({
                    'error': 'This trip is already cancelled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the trip has already started or ended
            if trip.start_date <= timezone.now():
                return Response({
                    'error': 'Cannot cancel a trip that has already started or ended'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if it's at least 3 days before the trip starts
            if trip.start_date - timezone.now() < timedelta(days=3):
                return Response({
                    'error': 'Trips can only be cancelled at least 3 days before the start date'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark the trip as cancelled and store cancellation information
            trip.status = 'cancelled'
            trip.cancelled_by = request.user
            trip.cancelled_at = timezone.now()
            trip.is_cancelled = True
            
            # Force save all fields and ensure the status is properly updated
            trip.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'is_cancelled'])
            
            # Double-check that the trip was actually marked as cancelled
            trip.refresh_from_db()
            logger.info(f'Trip {trip_id} status after save: {trip.status}')
            
            # Log the cancellation for debugging
            logger.info(f'Trip {trip_id} cancelled by user {request.user.username}')
            
            # Send cancellation notifications to all members
            create_trip_cancellation_notifications(trip, request.user)
            
            return Response({
                'message': 'Trip cancelled successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LeaveTripView(APIView):
    """View to leave a trip that the user has joined.
    
    Users can only leave trips they have joined (not created), and it must be at least 3 days before the trip starts.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, trip_id):
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            
            # Check if the user is a member of the trip
            if trip.creator == request.user:
                return Response({
                    'error': 'You are the creator of this trip, you cannot leave it. You must cancel it instead.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if request.user not in trip.members.all():
                return Response({
                    'error': 'You are not a member of this trip'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the trip is already canceled
            if trip.status == 'cancelled':
                return Response({
                    'error': 'This trip is already cancelled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the trip has already started or ended
            if trip.start_date <= timezone.now():
                return Response({
                    'error': 'Cannot leave a trip that has already started or ended'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if it's at least 3 days before the trip starts
            if trip.start_date - timezone.now() < timedelta(days=3):
                return Response({
                    'error': 'You can only leave a trip at least 3 days before the start date'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Remove the user from the trip members
            trip.members.remove(request.user)
            trip.save()
            
            # Send notifications to all members about user leaving the trip
            create_trip_leave_notifications(trip, request.user)
            
            return Response({
                'message': 'You have successfully left the trip'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConnectedBuddiesView(APIView):
    """View to retrieve the user's connected buddies."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get all trips created by or joined by the user
        created_trips = Trip.objects.filter(user=user)
        joined_trips = Trip.objects.filter(members=user)
        
        # Collect all buddies from these trips
        buddies = {}
        
        # Process created trips
        for trip in created_trips:
            # Get all members of trips created by the user
            for member in trip.members.all():
                if member.id != user.id:
                    if member.id in buddies:
                        buddies[member.id]['trips_together'] += 1
                    else:
                        buddies[member.id] = {
                            'id': member.id,
                            'username': member.username,
                            'first_name': member.first_name,
                            'last_name': member.last_name,
                            'profile_picture': member.profile_picture.url if member.profile_picture else None,
                            'trips_together': 1
                        }
        
        # Process joined trips
        for trip in joined_trips:
            # Add the trip creator if it's not the user
            if trip.user.id != user.id:
                if trip.user.id in buddies:
                    buddies[trip.user.id]['trips_together'] += 1
                else:
                    buddies[trip.user.id] = {
                        'id': trip.user.id,
                        'username': trip.user.username,
                        'first_name': trip.user.first_name,
                        'last_name': trip.user.last_name,
                        'profile_picture': trip.user.profile_picture.url if trip.user.profile_picture else None,
                        'trips_together': 1
                    }
            
            # Add other members
            for member in trip.members.all():
                if member.id != user.id:
                    if member.id in buddies:
                        buddies[member.id]['trips_together'] += 1
                    else:
                        buddies[member.id] = {
                            'id': member.id,
                            'username': member.username,
                            'first_name': member.first_name,
                            'last_name': member.last_name,
                            'profile_picture': member.profile_picture.url if member.profile_picture else None,
                            'trips_together': 1
                        }
        
        # Convert to list and sort by trips_together (descending)
        buddies_list = list(buddies.values())
        buddies_list.sort(key=lambda x: x['trips_together'], reverse=True)
        
        return Response(buddies_list)


def create_trip_join_notifications(trip, user):
    """
    Create notifications when a user joins a trip:
    1. Notify the trip creator that a new member joined
    2. Notify the user that they successfully joined the trip
    3. Notify other trip members that a new member joined
    """
    # Get trip creator and other members
    trip_creator = trip.user
    other_members = trip.members.exclude(id=user.id).exclude(id=trip_creator.id)
    
    # 1. Notify trip creator that a new member joined
    if trip_creator.id != user.id:
        TripNotification.objects.create(
            user=trip_creator,
            trip=trip,
            notification_type='new_member',
            message=f'{user.username} joined your trip "{trip.destination.name}".',
            related_user=user,
            is_read=False
        )
    
    # 2. Notify the user that they successfully joined the trip
    TripNotification.objects.create(
        user=user,
        trip=trip,
        notification_type='trip_joined',
        message=f'You have successfully joined "{trip.destination.name}".',
        related_user=None,
        is_read=False
    )
    
    # 3. Notify other trip members that a new member joined
    for member in other_members:
        TripNotification.objects.create(
            user=member,
            trip=trip,
            notification_type='new_member',
            message=f'{user.username} has joined "{trip.destination.name}" you\'re a part of.',
            related_user=user,
            is_read=False
        )

def create_trip_cancellation_notifications(trip, cancelling_user):
    """
    Create notifications when a trip is cancelled by the creator:
    1. Notify all members of the trip that it has been cancelled
    """
    # Get all members of the trip excluding the cancelling user
    members = trip.members.exclude(id=cancelling_user.id)
    
    # Notify all members that the trip has been cancelled
    for member in members:
        TripNotification.objects.create(
            user=member,
            trip=trip,
            notification_type='trip_cancelled',
            message=f'Trip "{trip.destination.name}" has been cancelled by {cancelling_user.username}.',
            related_user=cancelling_user,
            is_read=False
        )

def create_trip_leave_notifications(trip, leaving_user):
    """
    Create notifications when a user leaves a trip:
    1. Notify the trip creator that a member left
    2. Notify other trip members that a member left
    """
    # Get trip creator and other members
    trip_creator = trip.user
    other_members = trip.members.exclude(id=leaving_user.id).exclude(id=trip_creator.id)
    
    # 1. Notify trip creator that a member left (if creator is not the one leaving)
    if trip_creator.id != leaving_user.id:
        TripNotification.objects.create(
            user=trip_creator,
            trip=trip,
            notification_type='trip_left',
            message=f'{leaving_user.username} has left your trip to {trip.destination.name}.',
            related_user=leaving_user,
            is_read=False
        )
    
    # 2. Notify other trip members that a member left
    for member in other_members:
        TripNotification.objects.create(
            user=member,
            trip=trip,
            notification_type='trip_left',
            message=f'{leaving_user.username} has left the trip to {trip.destination.name}.',
            related_user=leaving_user,
            is_read=False
        )


def create_trip_member_removed_notifications(trip, removed_member, removing_user):
    """
    Create notifications when a member is removed from a trip by the creator:
    1. Notify the removed member that they have been removed
    2. Notify other trip members that a member was removed
    """
    # Get other members (excluding the removed member)
    other_members = trip.members.exclude(id=removed_member.id)
    
    # 1. Notify the removed member that they have been removed
    TripNotification.objects.create(
        user=removed_member,
        trip=trip,
        notification_type='trip_left',  # Reusing the trip_left type for simplicity
        message=f'You have been removed from the trip to {trip.destination.name} by the trip creator.',
        related_user=removing_user,
        is_read=False
    )
    
    # 2. Notify other trip members that a member was removed
    for member in other_members:
        if member.id != removing_user.id:  # Don't notify the removing user (trip creator)
            TripNotification.objects.create(
                user=member,
                trip=trip,
                notification_type='trip_left',  # Reusing the trip_left type for simplicity
                message=f'{removed_member.username} has been removed from the trip to {trip.destination.name}.',
                related_user=removed_member,
                is_read=False
            )


class TripNotificationView(APIView):
    """View to list and manage user's trip notifications."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all notifications for the current user
        notifications = TripNotification.objects.filter(user=request.user).order_by('-created_at')
        serializer = TripNotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Check if the request is to clear all notifications
        clear_all = request.data.get('clear_all', False)
        
        if clear_all:
            # Delete all notifications for the current user
            count = TripNotification.objects.filter(user=request.user).delete()[0]
            return Response({"message": f"All notifications cleared", "count": count}, status=status.HTTP_200_OK)
        
        # Mark notifications as read
        notification_ids = request.data.get('notification_ids', [])
        if not notification_ids:
            return Response({"error": "No notification IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        notifications = TripNotification.objects.filter(
            id__in=notification_ids,
            user=request.user
        )
        
        for notification in notifications:
            notification.mark_as_read()
            
        return Response({"message": f"{len(notifications)} notifications marked as read"})


class UnreadNotificationCountView(APIView):
    """View to get the count of unread notifications."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Count unread notifications for the current user
        unread_count = TripNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({"unread_count": unread_count})


class ChatNotificationView(APIView):
    """View to list and manage user's chat notifications."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all chat notifications for the current user
        notifications = ChatNotification.objects.filter(user=request.user).order_by('-created_at')
        serializer = ChatNotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Check if the request is to clear all notifications
        clear_all = request.data.get('clear_all', False)
        
        if clear_all:
            # Delete all chat notifications for the current user
            count = ChatNotification.objects.filter(user=request.user).delete()[0]
            return Response({"message": f"All chat notifications cleared", "count": count}, status=status.HTTP_200_OK)
        
        # Mark notifications as read
        notification_ids = request.data.get('notification_ids', [])
        if not notification_ids:
            return Response({"error": "No notification IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
            
        notifications = ChatNotification.objects.filter(
            id__in=notification_ids,
            user=request.user
        )
        
        for notification in notifications:
            notification.mark_as_read()
            
        return Response({"message": f"{len(notifications)} chat notifications marked as read"})


class UnreadChatNotificationCountView(APIView):
    """View to get the count of unread chat notifications."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Count unread chat notifications for the current user
        unread_count = ChatNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({"unread_count": unread_count})


class RemoveTripMemberView(APIView):
    """View to remove a member from a trip.
    
    Only the creator of the trip can remove members, and it must be at least 3 days before the trip starts.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, trip_id, member_id):
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            member = get_object_or_404(UserProfile, id=member_id)
            
            # Check if the user is the creator of the trip
            if trip.creator.id != request.user.id:
                return Response({
                    'error': 'Only the creator of the trip can remove members'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if the member is actually a member of the trip
            if member not in trip.members.all():
                return Response({
                    'error': 'This user is not a member of this trip'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the trip is already canceled
            if trip.status == 'cancelled':
                return Response({
                    'error': 'This trip is already cancelled'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the trip has already started or ended
            if trip.start_date <= timezone.now():
                return Response({
                    'error': 'Cannot remove members from a trip that has already started or ended'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if it's at least 3 days before the trip starts
            if trip.start_date - timezone.now() < timedelta(days=3):
                return Response({
                    'error': 'Members can only be removed at least 3 days before the start date'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Remove the member from the trip
            trip.members.remove(member)
            trip.save()
            
            # Create notification for the removed member
            create_trip_member_removed_notifications(trip, member, request.user)
            
            return Response({
                'message': f'{member.username} has been removed from the trip'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =====================================================
# AI/OpenTripMap Destination Recommendations
# =====================================================

class DestinationRecommendationsView(APIView):
    """
    AI-powered destination recommendations using OpenTripMap API.
    
    GET /api/ai/destination-recommendations/
    
    Query Parameters:
        - destination_id: ID of the PreferredDestination (optional)
        - latitude: Latitude for search (required if no destination_id)
        - longitude: Longitude for search (required if no destination_id)
        - radius: Search radius in meters (default: 5000)
        - limit: Max number of results (default: 10)
    
    Returns nearby places based on user's travel interests.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            from .services.open_trip_map import OpenTripMapService
            
            # Get query parameters
            destination_id = request.query_params.get('destination_id')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            radius = int(request.query_params.get('radius', 5000))
            limit_str = request.query_params.get('limit', '10')
            print(f"DEBUG: limit_str = {limit_str}, type = {type(limit_str)}")
            limit = int(limit_str)
            print(f"DEBUG: limit = {limit}, type = {type(limit)}")
            
            # Validate limit
            if limit < 1 or limit > 50:
                limit = 10
            
            # Get destination info if destination_id provided
            destination_info = None
            if destination_id:
                try:
                    destination = PreferredDestination.objects.get(id=destination_id)
                    destination_info = {
                        'id': destination.id,
                        'name': destination.name,
                        'location': destination.location
                    }
                except PreferredDestination.DoesNotExist:
                    return Response({
                        'error': 'Destination not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate coordinates
            if not latitude or not longitude:
                return Response({
                    'error': 'latitude and longitude are required query parameters'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except ValueError:
                return Response({
                    'error': 'latitude and longitude must be valid numbers'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user's travel interests
            user = request.user
            interests = []
            
            # Get interests - either from destination or use popular travel interests
            interests = []
            
            # If destination_id provided, get interests linked to that destination
            if destination_id:
                try:
                    destination = PreferredDestination.objects.get(id=destination_id)
                    # Get interests from DestinationTravelInterest
                    dest_interests = DestinationTravelInterest.objects.filter(destination=destination)
                    interests = [di.interest.name for di in list(dest_interests)]
                except PreferredDestination.DoesNotExist:
                    pass
                except Exception as e:
                    logger.warning(f"Error getting destination interests: {e}")
            
            # If no interests from destination, get some popular ones
            if not interests:
                try:
                    # Get all available travel interests as fallback
                    all_interests = list(TravelInterest.objects.all()[:5])
                    interests = [interest.name for interest in all_interests]
                except Exception as e:
                    logger.warning(f"Error getting travel interests: {e}")
            
            # If still no interests, use defaults
            if not interests:
                interests = ['sightseeing', 'cultural', 'nature']
            
            # Initialize OpenTripMap service and get recommendations
            service = OpenTripMapService()
            result = service.get_recommendations_for_interests(
                latitude=latitude,
                longitude=longitude,
                interests=interests,
                radius=radius,
                limit=limit
            )
            
            # Build response
            response_data = {
                'success': result.get('success', False),
                'destination': destination_info,
                'recommendations': result.get('places', []),
                'total_count': result.get('total_count', 0),
                'user_interests': interests,
                'mapped_categories': result.get('mapped_categories', []),
                'query_params': result.get('query_params', {})
            }
            
            if not result.get('success'):
                response_data['error'] = result.get('error', 'Unknown error')
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in DestinationRecommendationsView: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

