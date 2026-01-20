"""
OpenTripMap API Test Script

Run this script to test the AI Destination Recommendations endpoint.
Make sure the Django server is running on localhost:8000
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def login(username, password):
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/login/", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        return response.json().get('access')
    else:
        print(f"Login failed: {response.text}")
        return None

def test_destination_recommendations(token, lat=15.5527, lon=73.7623, limit=5):
    """Test the AI destination recommendations endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "latitude": lat,
        "longitude": lon,
        "limit": limit,
        "radius": 5000
    }
    
    print(f"\n🔍 Testing AI Destination Recommendations...")
    print(f"   Coordinates: ({lat}, {lon})")
    print(f"   Radius: 5000m, Limit: {limit}")
    
    response = requests.get(
        f"{BASE_URL}/ai/destination-recommendations/",
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS! Status: {response.status_code}")
        print(f"\n📊 Response Summary:")
        print(f"   - Success: {data.get('success')}")
        print(f"   - Total Places Found: {data.get('total_count')}")
        print(f"   - User Interests: {data.get('user_interests')}")
        print(f"   - Mapped Categories: {data.get('mapped_categories')}")
        
        if data.get('recommendations'):
            print(f"\n📍 Recommended Places:")
            for i, place in enumerate(data['recommendations'], 1):
                print(f"\n   {i}. {place.get('name', 'Unknown')}")
                print(f"      Categories: {', '.join(place.get('kinds', [])[:3])}")
                print(f"      Distance: {place.get('distance', 0):.0f}m")
                if place.get('wikipedia_extract'):
                    print(f"      Description: {place['wikipedia_extract'][:100]}...")
        else:
            print("\n   No recommendations found for this location.")
        
        return data
    else:
        print(f"\n❌ FAILED! Status: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def main():
    print("=" * 60)
    print("OpenTripMap API Integration Test")
    print("=" * 60)
    
    # Get credentials from user
    print("\nEnter your login credentials:")
    username = input("Username/Email: ")
    password = input("Password: ")
    
    # Login
    print("\n🔐 Logging in...")
    token = login(username, password)
    
    if not token:
        print("❌ Could not authenticate. Please check your credentials.")
        return
    
    print("✅ Successfully logged in!")
    
    # Test different locations
    test_locations = [
        ("Goa, India", 15.5527, 73.7623),
        ("Paris, France", 48.8566, 2.3522),
        ("Bali, Indonesia", -8.3405, 115.0920),
    ]
    
    print("\nWhich location would you like to test?")
    for i, (name, lat, lon) in enumerate(test_locations, 1):
        print(f"  {i}. {name} ({lat}, {lon})")
    print(f"  {len(test_locations) + 1}. Enter custom coordinates")
    
    choice = input("\nEnter choice (1-4): ")
    
    try:
        choice = int(choice)
        if 1 <= choice <= len(test_locations):
            name, lat, lon = test_locations[choice - 1]
        else:
            lat = float(input("Enter latitude: "))
            lon = float(input("Enter longitude: "))
    except:
        lat, lon = 15.5527, 73.7623  # Default to Goa
    
    # Run test
    test_destination_recommendations(token, lat, lon)
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
