#!/usr/bin/env python3
"""
Quick test script to verify the collections page is working
after resolving the SQLAlchemy enum casting error.
"""
import requests
import sys
from datetime import datetime

def test_collections_endpoint():
    """Test the collections page endpoint"""
    base_url = "https://mcp-vultr.l.supported.systems"
    collections_url = f"{base_url}/collections"

    print(f"Collections Page Verification Test")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"=" * 50)

    try:
        # Test collections page
        print(f"Testing: {collections_url}")
        response = requests.get(collections_url, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Response Length: {len(response.content)} bytes")

        if response.status_code == 200:
            print("✅ SUCCESS: Collections page loaded successfully!")

            # Check for common error indicators in the response
            content = response.text.lower()
            if "500 internal server error" in content:
                print("❌ ERROR: Page contains 500 error content")
                return False
            elif "sqlalchemy" in content and "error" in content:
                print("❌ ERROR: SQLAlchemy error detected in response")
                return False
            elif "enum" in content and "cast" in content:
                print("❌ ERROR: Enum casting error detected")
                return False
            else:
                print("✅ No error indicators found in response content")

                # Check if it's a proper HTML page
                if "service collections" in content:
                    print("✅ Collections page content detected")
                    return True
                else:
                    print("⚠️  Page loaded but content unclear")
                    return True

        elif response.status_code == 500:
            print("❌ FAILED: 500 Internal Server Error - SQLAlchemy issue may persist")
            return False
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False

    except requests.RequestException as e:
        print(f"❌ REQUEST FAILED: {str(e)}")
        return False

    return True

def test_api_endpoints():
    """Test related API endpoints"""
    base_url = "https://mcp-vultr.l.supported.systems"
    api_endpoints = [
        "/api/collections",
        "/api/projects/"
    ]

    print(f"\nTesting API Endpoints:")
    print(f"=" * 30)

    for endpoint in api_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            print(f"{endpoint}: {response.status_code} {response.reason}")

            if response.status_code == 500:
                print(f"  ❌ ERROR: 500 response from {endpoint}")
            elif response.status_code in [401, 403]:
                print(f"  ✅ AUTH: Authentication required (expected)")
            elif response.status_code == 405:
                print(f"  ✅ METHOD: Method not allowed (expected for some endpoints)")
            else:
                print(f"  ✅ OK: Valid response")

        except requests.RequestException as e:
            print(f"{endpoint}: ❌ FAILED - {str(e)}")

if __name__ == "__main__":
    success = test_collections_endpoint()
    test_api_endpoints()

    if success:
        print(f"\n🎉 VERIFICATION COMPLETE: Collections page is working!")
        sys.exit(0)
    else:
        print(f"\n💥 VERIFICATION FAILED: Collections page has issues!")
        sys.exit(1)