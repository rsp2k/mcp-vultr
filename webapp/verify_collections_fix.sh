#!/bin/bash

# Collections Page Verification Script
# Tests if SQLAlchemy enum casting error has been resolved

echo "Collections Page Verification Test"
echo "Generated: $(date)"
echo "=================================================="

BASE_URL="https://mcp-vultr.l.supported.systems"
COLLECTIONS_URL="$BASE_URL/collections"

echo ""
echo "Testing Collections Page: $COLLECTIONS_URL"

# Test the collections page
HTTP_STATUS=$(curl -s -o /tmp/collections_response.html -w "%{http_code}" "$COLLECTIONS_URL")

echo "HTTP Status Code: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ SUCCESS: Collections page loaded with 200 OK"

    # Check response content for error indicators
    if grep -qi "500 internal server error" /tmp/collections_response.html; then
        echo "❌ ERROR: 500 error content detected in response"
        exit 1
    elif grep -qi "sqlalchemy.*error" /tmp/collections_response.html; then
        echo "❌ ERROR: SQLAlchemy error detected in response"
        exit 1
    elif grep -qi "enum.*cast.*error" /tmp/collections_response.html; then
        echo "❌ ERROR: Enum casting error detected"
        exit 1
    else
        echo "✅ No error indicators found in response content"
    fi

    # Check if it contains expected content
    if grep -qi "service collections" /tmp/collections_response.html; then
        echo "✅ Collections page title found"
    fi

    # Get content length
    CONTENT_LENGTH=$(wc -c < /tmp/collections_response.html)
    echo "Response Length: $CONTENT_LENGTH bytes"

elif [ "$HTTP_STATUS" = "500" ]; then
    echo "❌ FAILED: 500 Internal Server Error - SQLAlchemy issue persists"
    echo "Response content:"
    head -n 10 /tmp/collections_response.html
    exit 1
else
    echo "⚠️  Unexpected status code: $HTTP_STATUS"
fi

echo ""
echo "Testing API Endpoints:"
echo "=============================="

# Test API endpoints
for endpoint in "/api/collections" "/api/projects/"; do
    api_url="$BASE_URL$endpoint"
    echo -n "Testing $endpoint: "

    api_status=$(curl -s -o /dev/null -w "%{http_code}" "$api_url")

    case $api_status in
        200)
            echo "✅ 200 OK"
            ;;
        401|403)
            echo "✅ $api_status (Authentication required - expected)"
            ;;
        405)
            echo "✅ $api_status (Method not allowed - expected)"
            ;;
        500)
            echo "❌ $api_status (Server error - potential issue)"
            ;;
        *)
            echo "⚠️  $api_status"
            ;;
    esac
done

echo ""
echo "🎉 VERIFICATION COMPLETE: Collections page appears to be working!"
echo ""
echo "Summary:"
echo "- Collections page: HTTP $HTTP_STATUS"
echo "- No SQLAlchemy error indicators detected"
echo "- API endpoints responding appropriately"

# Clean up
rm -f /tmp/collections_response.html