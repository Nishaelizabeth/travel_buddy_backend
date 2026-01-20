"""
OpenTripMap API Service
Provides integration with OpenTripMap API for destination recommendations.

API Documentation: https://opentripmap.io/docs
"""

import requests
import logging
from typing import List, Dict, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenTripMapService:
    """
    Service class for interacting with OpenTripMap API.
    """
    
    BASE_URL = "https://api.opentripmap.com/0.1/en"
    
    # Mapping of TravelInterest names to OpenTripMap categories
    INTEREST_CATEGORY_MAP = {
        # Nature & Outdoors
        'beach': 'beaches',
        'beaches': 'beaches',
        'nature': 'natural',
        'hiking': 'natural,mountains',
        'mountains': 'mountains',
        'wildlife': 'wildlife_reserves',
        'parks': 'parks',
        
        # Adventure & Sports
        'adventure': 'sport,amusements',
        'sports': 'sport',
        'water sports': 'sport,beaches',
        'diving': 'diving',
        
        # Culture & History
        'culture': 'cultural',
        'cultural': 'cultural',
        'history': 'historic',
        'historical': 'historic',
        'museums': 'museums',
        'art': 'museums,cultural',
        'architecture': 'architecture',
        'temples': 'religion',
        'religious': 'religion',
        
        # Food & Entertainment
        'food': 'foods',
        'cuisine': 'foods',
        'nightlife': 'amusements',
        'entertainment': 'amusements',
        'shopping': 'shops',
        
        # Relaxation
        'spa': 'health',
        'wellness': 'health',
        'relaxation': 'beaches,health',
        
        # Default
        'sightseeing': 'interesting_places',
        'photography': 'view_points',
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenTripMap service.
        
        Args:
            api_key: OpenTripMap API key. If not provided, reads from settings.
        """
        self.api_key = api_key or getattr(settings, 'OPENTRIPMAP_API_KEY', None)
        
        if not self.api_key:
            # Use the configured API key
            self.api_key = "5ae2e3f221c38a28845f05b6e59e584ccfd26855d205a83c5d74da4c"
    
    def map_interest_to_category(self, interest_name: str) -> str:
        """
        Map a TravelInterest name to OpenTripMap category.
        
        Args:
            interest_name: Name of the travel interest
            
        Returns:
            OpenTripMap category string
        """
        # Normalize interest name
        normalized = interest_name.lower().strip()
        
        # Try exact match first
        if normalized in self.INTEREST_CATEGORY_MAP:
            return self.INTEREST_CATEGORY_MAP[normalized]
        
        # Try partial match
        for key, value in self.INTEREST_CATEGORY_MAP.items():
            if key in normalized or normalized in key:
                return value
        
        # Default to interesting places
        return 'interesting_places'
    
    def get_places_by_radius(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        kinds: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Fetch nearby places using OpenTripMap Radius API.
        
        Args:
            latitude: Latitude of the center point
            longitude: Longitude of the center point
            radius: Search radius in meters (default: 5000m)
            kinds: Comma-separated category filters
            limit: Maximum number of results (default: 10)
            
        Returns:
            Dict containing places and metadata
        """
        endpoint = f"{self.BASE_URL}/places/radius"
        
        params = {
            'lat': latitude,
            'lon': longitude,
            'radius': radius,
            'limit': limit,
            'apikey': self.api_key,
            'format': 'json'
        }
        
        if kinds:
            params['kinds'] = kinds
        
        try:
            logger.info(f"Fetching places from OpenTripMap: lat={latitude}, lon={longitude}, kinds={kinds}")
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            
            places = response.json()
            
            # Enrich places with additional details
            enriched_places = []
            for place in places[:limit]:
                enriched = self._enrich_place(place)
                if enriched:
                    enriched_places.append(enriched)
            
            return {
                'success': True,
                'places': enriched_places,
                'total_count': len(enriched_places),
                'query_params': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': radius,
                    'categories': kinds
                }
            }
            
        except requests.exceptions.Timeout:
            logger.error("OpenTripMap API request timed out")
            return {
                'success': False,
                'error': 'Request timed out',
                'places': [],
                'total_count': 0
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenTripMap API HTTP error: {e}")
            return {
                'success': False,
                'error': f'API error: {e.response.status_code}',
                'places': [],
                'total_count': 0
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenTripMap API request failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'places': [],
                'total_count': 0
            }
        except ValueError as e:
            logger.error(f"Failed to parse OpenTripMap response: {e}")
            return {
                'success': False,
                'error': 'Invalid response format',
                'places': [],
                'total_count': 0
            }
    
    def _enrich_place(self, place: Dict) -> Optional[Dict]:
        """
        Enrich a place with additional details from the xid endpoint.
        
        Args:
            place: Basic place data from radius search
            
        Returns:
            Enriched place data or None if failed
        """
        if not place.get('xid'):
            return None
        
        try:
            # Get detailed info for the place
            detail_endpoint = f"{self.BASE_URL}/places/xid/{place['xid']}"
            response = requests.get(
                detail_endpoint,
                params={'apikey': self.api_key},
                timeout=5
            )
            
            if response.status_code == 200:
                details = response.json()
                
                return {
                    'name': details.get('name') or place.get('name', 'Unknown'),
                    'kinds': details.get('kinds', '').split(',') if details.get('kinds') else [],
                    'distance': place.get('dist', 0),
                    'coordinates': {
                        'lat': details.get('point', {}).get('lat') or place.get('point', {}).get('lat'),
                        'lon': details.get('point', {}).get('lon') or place.get('point', {}).get('lon')
                    },
                    'wikipedia_extract': details.get('wikipedia_extracts', {}).get('text', ''),
                    'preview': details.get('preview', {}).get('source', ''),
                    'xid': place.get('xid')
                }
            else:
                # Return basic info if detail fetch fails
                return {
                    'name': place.get('name', 'Unknown'),
                    'kinds': place.get('kinds', '').split(',') if place.get('kinds') else [],
                    'distance': place.get('dist', 0),
                    'coordinates': {
                        'lat': place.get('point', {}).get('lat'),
                        'lon': place.get('point', {}).get('lon')
                    },
                    'wikipedia_extract': '',
                    'preview': '',
                    'xid': place.get('xid')
                }
                
        except Exception as e:
            logger.warning(f"Failed to enrich place {place.get('xid')}: {e}")
            return {
                'name': place.get('name', 'Unknown'),
                'kinds': place.get('kinds', '').split(',') if place.get('kinds') else [],
                'distance': place.get('dist', 0),
                'coordinates': {
                    'lat': place.get('point', {}).get('lat'),
                    'lon': place.get('point', {}).get('lon')
                },
                'wikipedia_extract': '',
                'preview': '',
                'xid': place.get('xid')
            }
    
    def get_recommendations_for_interests(
        self,
        latitude: float,
        longitude: float,
        interests: List[str],
        radius: int = 5000,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get place recommendations based on user interests.
        
        Args:
            latitude: Latitude of the destination
            longitude: Longitude of the destination
            interests: List of TravelInterest names
            radius: Search radius in meters
            limit: Maximum number of results per category
            
        Returns:
            Dict containing recommendations grouped by interest
        """
        # Map interests to OpenTripMap categories
        categories = set()
        for interest in interests:
            category = self.map_interest_to_category(interest)
            categories.update(category.split(','))
        
        # Join categories for API call
        kinds = ','.join(categories)
        
        # Fetch places
        result = self.get_places_by_radius(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            kinds=kinds,
            limit=limit
        )
        
        if result['success']:
            result['mapped_categories'] = list(categories)
            result['original_interests'] = interests
        
        return result
