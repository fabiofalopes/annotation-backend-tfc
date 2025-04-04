#!/usr/bin/env python3
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import os
from pathlib import Path

class APITestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.test_project_id = None
        self.test_container_ids = []  # Store multiple container IDs
        self.test_message_ids = []    # Store message IDs for annotations
        
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Make an HTTP request to the API"""
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{self.base_url}{endpoint}"
        
        if files:
            response = requests.request(method, url, headers=headers, files=files)
        else:
            if data and method != "GET":
                headers["Content-Type"] = "application/json"
                response = requests.request(method, url, headers=headers, json=data)
            elif data and method == "GET":
                response = requests.request(method, url, headers=headers, params=data)
            else:
                response = requests.request(method, url, headers=headers)
        
        return response

    def test_admin_auth(self, email: str = "admin@example.com", password: str = "admin") -> bool:
        """Test admin authentication"""
        print("\n=== Testing Admin Authentication ===")
        
        # Try to login as admin
        data = {
            "username": email,
            "password": password
        }
        response = requests.post(
            f"{self.base_url}/auth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
            print("✅ Admin login successful")
            return True
        else:
            print("❌ Admin login failed:", response.json())
            return False

    def test_create_test_user(self, email: str = "test@example.com", password: str = "test123") -> bool:
        """Test creating a regular user"""
        print("\n=== Testing User Creation ===")
        
        data = {
            "email": email,
            "password": password,
            "is_admin": False
        }
        
        response = self._make_request("POST", "/auth/register", data=data)
        
        if response.status_code in [200, 201, 400]:  # 400 means user might already exist
            print("✅ User creation successful or user already exists")
            return True
        else:
            print("❌ User creation failed:", response.json())
            return False

    def test_user_auth(self, email: str = "test@example.com", password: str = "test123") -> bool:
        """Test user authentication"""
        print("\n=== Testing User Authentication ===")
        
        data = {
            "username": email,
            "password": password
        }
        response = requests.post(
            f"{self.base_url}/auth/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            self.user_token = response.json()["access_token"]
            print("✅ User login successful")
            return True
        else:
            print("❌ User login failed:", response.json())
            return False

    def test_create_project(self, name: str = "Test Chat Project") -> bool:
        """Test creating a new project"""
        print("\n=== Testing Project Creation ===")
        
        data = {
            "name": name,
            "type": "chat_disentanglement",
            "description": "A test project for chat disentanglement"
        }
        
        response = self._make_request("POST", "/admin/projects", data=data, token=self.admin_token)
        
        if response.status_code in [200, 201]:
            self.test_project_id = response.json()["id"]
            print("✅ Project creation successful")
            return True
        else:
            print("❌ Project creation failed:", response.json())
            return False

    def test_assign_user_to_project(self) -> bool:
        """Test assigning a user to the project"""
        print("\n=== Testing Project Assignment ===")
        
        response = self._make_request(
            "POST",
            f"/projects/{self.test_project_id}/assign/1",  # Assuming user ID is 1
            token=self.admin_token
        )
        
        if response.status_code in [200, 201, 204]:  # 204 means success with no content
            print("✅ User assignment successful")
            return True
        else:
            print("❌ User assignment failed:", response.text)
            return False

    def test_import_multiple_chat_files(self) -> bool:
        """Test importing multiple chat data files"""
        print("\n=== Testing Multiple Chat Data Imports ===")
        
        test_files = [
            "uploads/VAC_R10.csv",
            "uploads/VAC_R10-fabio.csv",
            "uploads/VAC_R10-zuil.csv",
            "uploads/VAC_R10-fabio-cp.csv",
            "uploads/VAC_R10-zuil-cp.csv"
        ]
        
        success = True
        for file_path in test_files:
            if not os.path.exists(file_path):
                print(f"❌ Test file {file_path} not found")
                continue
                
            # Prepare import request
            import_data = {
                "project_id": self.test_project_id,
                "container_name": f"Test Container - {Path(file_path).stem}",
                "import_type": "chat",
                "column_mapping": {
                    "user_id": "user_id",
                    "turn_id": "turn_id",
                    "turn_text": "turn_text",
                    "reply_to_turn": "reply_to_turn"
                }
            }
            
            files = {
                'file': (Path(file_path).name, open(file_path, 'rb'), 'text/csv'),
                'import_request': (None, json.dumps(import_data), 'application/json')
            }
            
            response = self._make_request(
                "POST",
                "/chat-disentanglement/import",
                files=files,
                token=self.admin_token
            )
            
            if response.status_code in [200, 201]:
                container_id = int(response.json()["id"])
                self.test_container_ids.append(container_id)
                print(f"✅ Successfully imported {file_path}")
                
                # Store first few message IDs for annotation tests
                messages_response = self._make_request(
                    "GET",
                    f"/chat-disentanglement/containers/{container_id}/messages?limit=5",
                    token=self.user_token
                )
                if messages_response.status_code == 200:
                    message_ids = [msg["id"] for msg in messages_response.json()]
                    self.test_message_ids.extend(message_ids)
            else:
                print(f"❌ Failed to import {file_path}:", response.text)
                success = False
        
        return success

    def test_create_diverse_annotations(self) -> bool:
        """Test creating different types of thread annotations"""
        print("\n=== Testing Diverse Thread Annotations ===")
        
        if not self.test_message_ids:
            print("❌ No message IDs available for annotation")
            return False
        
        # Different types of annotations to test
        test_annotations = [
            {
                "thread_id": "pro_vaccination",
                "confidence": 0.9,
                "notes": "Strong pro-vaccination argument",
                "type": "thread",
                "data": {"sentiment": "positive"}
            },
            {
                "thread_id": "anti_vaccination",
                "confidence": 0.8,
                "notes": "Anti-vaccination perspective",
                "type": "thread",
                "data": {"sentiment": "negative"}
            },
            {
                "thread_id": "neutral_discussion",
                "confidence": 0.7,
                "notes": "Neutral discussion about vaccines",
                "type": "thread",
                "data": {"sentiment": "neutral"}
            }
        ]
        
        success = True
        for i, (message_id, annotation) in enumerate(zip(self.test_message_ids[:3], test_annotations)):
            response = self._make_request(
                "POST",
                f"/chat-disentanglement/messages/{message_id}/thread",
                data=annotation,
                token=self.user_token
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Created diverse annotation {i+1} for message {message_id}")
            else:
                print(f"❌ Failed to create annotation {i+1}:", response.text)
                success = False
        
        return success

    def test_list_and_verify_annotations(self) -> bool:
        """Test listing and verifying annotations across containers"""
        print("\n=== Testing Annotation Listing and Verification ===")
        
        if not self.test_container_ids:
            print("❌ No container IDs available")
            return False
        
        success = True
        thread_counts = {}
        
        for container_id in self.test_container_ids:
            response = self._make_request(
                "GET",
                f"/chat-disentanglement/containers/{container_id}/threads",
                token=self.user_token
            )
            
            if response.status_code == 200:
                threads = response.json()
                thread_counts[container_id] = {
                    "total_threads": len(threads),
                    "thread_ids": list(threads.keys())
                }
                print(f"✅ Container {container_id} has {len(threads)} threads")
                print(f"   Thread IDs: {', '.join(threads.keys())}")
            else:
                print(f"❌ Failed to list threads for container {container_id}:", response.text)
                success = False
        
        # Print summary of annotations across containers
        print("\nAnnotation Summary:")
        for container_id, counts in thread_counts.items():
            print(f"Container {container_id}:")
            print(f"  - Total threads: {counts['total_threads']}")
            print(f"  - Unique thread IDs: {counts['thread_ids']}")
        
        return success

    def test_list_messages(self) -> bool:
        """Test listing messages from a container"""
        print("\n=== Testing Message Listing ===")
        
        if not self.test_container_ids:
            print("❌ No container IDs available")
            return False
        
        success = True
        for container_id in self.test_container_ids:
            response = self._make_request(
                "GET",
                f"/chat-disentanglement/containers/{container_id}/messages",
                token=self.user_token
            )
            
            if response.status_code == 200:
                messages = response.json()
                print(f"✅ Successfully retrieved {len(messages)} messages from container {container_id}")
                if messages:
                    print("First message:", json.dumps(messages[0], indent=2))
            else:
                print(f"❌ Message listing failed for container {container_id}:", response.text)
                success = False
        
        return success

    def test_create_thread_annotations(self) -> bool:
        """Test creating thread annotations"""
        print("\n=== Testing Thread Annotation Creation ===")
        
        if not self.test_container_ids:
            print("❌ No container IDs available")
            return False
        
        # Create annotations for the first two messages in each container
        success = True
        for container_id in self.test_container_ids:
            messages_response = self._make_request(
                "GET",
                f"/chat-disentanglement/containers/{container_id}/messages?limit=2",
                token=self.user_token
            )
            
            if messages_response.status_code == 200:
                messages = messages_response.json()
                for i, message in enumerate(messages, start=1):
                    response = self._make_request(
                        "POST",
                        f"/chat-disentanglement/messages/{message['id']}/thread",
                        data={
                            "thread_id": f"container_{container_id}_message_{i}",
                            "confidence": 1.0,
                            "notes": f"Annotation for message {i} in container {container_id}",
                            "type": "thread",
                            "data": {}
                        },
                        token=self.user_token
                    )
                    
                    if response.status_code in [200, 201]:
                        print(f"✅ Created annotation for message {i} in container {container_id}")
                    else:
                        print(f"❌ Failed to create annotation for message {i} in container {container_id}:", response.text)
                        success = False
            else:
                print(f"❌ Failed to retrieve messages from container {container_id}:", messages_response.text)
                success = False
        
        return success

    def test_list_thread_annotations(self) -> bool:
        """Test listing thread annotations"""
        print("\n=== Testing Thread Annotation Listing ===")
        
        if not self.test_container_ids:
            print("❌ No container IDs available")
            return False
        
        success = True
        for container_id in self.test_container_ids:
            response = self._make_request(
                "GET",
                f"/chat-disentanglement/containers/{container_id}/threads",
                token=self.user_token
            )
            
            if response.status_code == 200:
                threads = response.json()
                print(f"✅ Successfully retrieved thread annotations for container {container_id}")
                print("Threads:", json.dumps(threads, indent=2))
            else:
                print(f"❌ Failed to list threads for container {container_id}:", response.text)
                success = False
        
        return success

    def run_all_tests(self):
        """Run all tests in sequence"""
        tests = [
            self.test_admin_auth,
            self.test_create_test_user,
            self.test_user_auth,
            self.test_create_project,
            self.test_assign_user_to_project,
            self.test_import_multiple_chat_files,
            self.test_create_diverse_annotations,
            self.test_list_and_verify_annotations,
            self.test_list_messages,
            self.test_create_thread_annotations,
            self.test_list_thread_annotations
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append((test.__name__, result))
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with error:", str(e))
                results.append((test.__name__, False))
        
        print("\n=== Test Summary ===")
        for test_name, result in results:
            status = "✅ Passed" if result else "❌ Failed"
            print(f"{test_name}: {status}")

if __name__ == "__main__":
    test_suite = APITestSuite()
    test_suite.run_all_tests() 