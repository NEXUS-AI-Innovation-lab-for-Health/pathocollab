import pytest
from fastapi import status

def test_register_user(client, test_user_data):
    """Test user registration"""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["full_name"] == test_user_data["full_name"]
    assert data["role"] == test_user_data["role"]
    assert "id" in data
    assert "hashed_password" not in data  # Should not return password

def test_register_duplicate_email(client, test_user_data):
    """Test registering with duplicate email"""
    # Register first time
    client.post("/api/auth/register", json=test_user_data)
    # Try to register again with same email
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"].lower()

def test_login_success(client, test_user_data):
    """Test successful login"""
    # Register user first
    client.post("/api/auth/register", json=test_user_data)
    
    # Login
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, test_user_data):
    """Test login with wrong password"""
    # Register user
    client.post("/api/auth/register", json=test_user_data)
    
    # Try to login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "WrongPassword123!"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    """Test login with non-existent user"""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
