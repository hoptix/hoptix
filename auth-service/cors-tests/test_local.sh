#!/bin/bash

# Local CORS Test Script for Auth Service
# Usage: ./test_local.sh [port]

PORT=${1:-"8080"}
SERVICE_URL="http://localhost:$PORT"
ORIGIN="http://localhost:3000"

echo "🧪 Testing CORS for Local Auth Service"
echo "Service URL: $SERVICE_URL"
echo "Origin: $ORIGIN"
echo "================================"

# Test 1: Health check first
echo "1️⃣  Testing Health Check"
echo "------------------------"
curl -i -X GET "$SERVICE_URL/health" 2>/dev/null | head -10
echo ""

# Test 2: Preflight request (OPTIONS) for signup
echo "2️⃣  Testing Preflight Request (OPTIONS /signup)"
echo "-----------------------------------------------"
curl -i -X OPTIONS \
  -H "Origin: $ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  "$SERVICE_URL/signup" 2>/dev/null | head -15
echo ""

# Test 3: POST request to signup endpoint
echo "3️⃣  Testing POST Request (/signup)"
echo "----------------------------------"
curl -i -X POST \
  -H "Origin: $ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testPassword123!"}' \
  "$SERVICE_URL/signup" 2>/dev/null | head -20
echo ""

# Test 4: POST request to token endpoint
echo "4️⃣  Testing POST Request (/token)"
echo "--------------------------------"
curl -i -X POST \
  -H "Origin: $ORIGIN" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testPassword123!"}' \
  "$SERVICE_URL/token?grant_type=password" 2>/dev/null | head -20
echo ""

echo "✅ Local CORS testing complete!"
echo ""
echo "Expected results:"
echo "- Health check should return 200 OK"
echo "- OPTIONS requests should return 200 OK with CORS headers"
echo "- POST requests should return proper status codes with CORS headers"
echo "- All responses should include 'Access-Control-Allow-Origin' header" 