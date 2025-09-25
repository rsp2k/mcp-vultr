#!/usr/bin/env python3
"""Test script for projects API functionality."""

import asyncio
import httpx
import os
import sys
from datetime import datetime, timedelta
import jwt

# JWT configuration (matching backend settings)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"

def create_test_jwt_token(user_id: str, email: str) -> str:
    """Create a test JWT token for API testing."""
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "exp": now + timedelta(hours=1),
        "iat": now,
        "iss": "service-collection-webapp",
        "aud": "service-collection-api"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def test_projects_api():
    """Test the projects API endpoints."""
    base_url = "https://mcp-vultr.l.supported.systems"

    # Create JWT token for our test user
    user_id = "3dcd2e48-90da-4b0d-a56c-98e4808c7c9a"
    user_email = "rpm@malloys.us"
    token = create_test_jwt_token(user_id, user_email)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(verify=False) as client:
        print("🔐 Testing Projects API Authentication & Functionality")
        print(f"📧 User: {user_email}")
        print(f"🆔 User ID: {user_id}")
        print(f"🎫 JWT Token: {token[:50]}...")
        print()

        # Test 1: List projects
        print("📋 TEST 1: List Projects")
        try:
            response = await client.get(f"{base_url}/api/projects/", headers=headers)
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                projects = response.json()
                print(f"   ✅ Success! Found {len(projects)} project(s)")

                for project in projects:
                    print(f"   📁 Project: {project['name']} ({project['slug']})")
                    print(f"      Role: {project.get('user_role', 'Unknown')}")
                    print(f"      Status: {project['status']}")
                    print(f"      Members: {project['member_count']}")
                    print(f"      Collections: {project['collection_count']}")

            else:
                print(f"   ❌ Failed: {response.text}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

        print()

        # Test 2: Get specific project details
        if response.status_code == 200 and projects:
            project_id = projects[0]['id']
            print(f"📄 TEST 2: Get Project Details ({project_id})")
            try:
                response = await client.get(f"{base_url}/api/projects/{project_id}", headers=headers)
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    project = response.json()
                    print(f"   ✅ Success! Project details retrieved")
                    print(f"   📁 Name: {project['name']}")
                    print(f"   🔗 Slug: {project['slug']}")
                    print(f"   📝 Description: {project.get('description', 'No description')}")
                    print(f"   👤 User Role: {project.get('user_role', 'Unknown')}")
                else:
                    print(f"   ❌ Failed: {response.text}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")

        print()

        # Test 3: List project members
        if response.status_code == 200 and projects:
            project_id = projects[0]['id']
            print(f"👥 TEST 3: List Project Members ({project_id})")
            try:
                response = await client.get(f"{base_url}/api/projects/{project_id}/members", headers=headers)
                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    members = response.json()
                    print(f"   ✅ Success! Found {len(members)} member(s)")

                    for member in members:
                        print(f"   👤 {member['email']} - {member['role']} {'(Owner)' if member['is_owner'] else ''}")

                else:
                    print(f"   ❌ Failed: {response.text}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")

        print()

        # Test 4: Create a new project
        print("🆕 TEST 4: Create New Project")
        new_project_data = {
            "name": f"Test Project {datetime.now().strftime('%H%M%S')}",
            "description": "Automated test project created by API test script",
            "color": "#2563eb",
            "settings": {"test": True}
        }

        try:
            response = await client.post(
                f"{base_url}/api/projects/",
                headers=headers,
                json=new_project_data
            )
            print(f"   Status: {response.status_code}")

            if response.status_code == 201:
                new_project = response.json()
                print(f"   ✅ Success! Created project")
                print(f"   📁 Name: {new_project['name']}")
                print(f"   🔗 Slug: {new_project['slug']}")
                print(f"   🆔 ID: {new_project['id']}")
                print(f"   👤 User Role: {new_project.get('user_role', 'Unknown')}")

                created_project_id = new_project['id']

                # Clean up - delete the test project
                print(f"   🗑️  Cleaning up test project...")
                delete_response = await client.delete(
                    f"{base_url}/api/projects/{created_project_id}",
                    headers=headers
                )
                if delete_response.status_code == 204:
                    print(f"   ✅ Test project deleted successfully")
                else:
                    print(f"   ⚠️  Failed to delete test project: {delete_response.status_code}")

            else:
                print(f"   ❌ Failed: {response.text}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Projects API Test Suite")
    print("=" * 50)
    asyncio.run(test_projects_api())
    print("=" * 50)
    print("✨ Test Suite Complete")