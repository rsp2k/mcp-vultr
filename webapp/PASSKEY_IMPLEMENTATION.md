# 🔐 WebAuthn PassKey Implementation Guide

A comprehensive enterprise-grade PassKey authentication system for secure confirmations in the Service Collection Management webapp.

## 🏗️ Architecture Overview

This implementation provides a complete WebAuthn-compliant PassKey system for securing sensitive operations like deployments, resource modifications, and administrative actions.

### Core Components

1. **Database Models** - Complete credential and session management
2. **REST API Endpoints** - WebAuthn challenge/response handling
3. **Frontend Integration** - User-friendly PassKey management
4. **Reusable Utilities** - Drop-in secure confirmation dialogs

## 📋 Features

### ✅ Security Features
- **WebAuthn 2.0 Compliant** - Full specification compliance
- **Cryptographically Secure Challenges** - 32-byte random challenges
- **Replay Protection** - Sign count tracking and validation
- **Origin Validation** - Proper domain verification
- **Audit Logging** - Complete operation tracking
- **Session Management** - Authentication session monitoring

### ✅ User Experience
- **Seamless Registration** - One-click PassKey creation
- **Secure Confirmations** - Modal-based authentication prompts
- **Profile Management** - Complete PassKey lifecycle management
- **Cross-Platform Support** - Works with all WebAuthn authenticators
- **Graceful Degradation** - Handles unsupported browsers

### ✅ Developer Experience
- **Reusable Components** - Drop-in JavaScript utilities
- **TypeScript Ready** - Proper type definitions
- **Comprehensive API** - Full CRUD operations
- **Docker Integration** - Container-ready deployment
- **Hot Reload Support** - Development-friendly setup

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ with npm/yarn
- Python 3.11+ with uv
- PostgreSQL 16+
- Docker & Docker Compose
- Modern browser with WebAuthn support

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd webapp
   ```

2. **Environment Configuration**
   ```bash
   # Copy and configure environment
   cp .env.example .env

   # Key configurations for PassKey:
   DOMAIN=your-domain.com
   DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
   ```

3. **Database Migration**
   ```bash
   # Run migrations to create PassKey tables
   docker compose exec vultr-backend alembic upgrade head
   ```

4. **Start Services**
   ```bash
   docker compose up -d
   ```

## 🔧 Database Schema

### ConnectedAccount Model
```python
class ConnectedAccount(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    provider_type = Column(Enum(ProviderType), nullable=False)
    provider_account_id = Column(String(255), nullable=False)
    access_token_hash = Column(String(255))
    provider_data = Column(JSON, default=dict)
    scopes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### PassKey Model
```python
class PassKey(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    credential_id = Column(String(255), unique=True, nullable=False)
    public_key = Column(Text, nullable=False)
    sign_count = Column(Integer, default=0)
    name = Column(String(100), nullable=False)
    authenticator_type = Column(Enum(PassKeyAuthenticatorType))
    transport_methods = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
```

## 🔌 API Endpoints

### PassKey Management

#### Register PassKey
```http
POST /api/auth/passkeys/registration-challenge
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "passkey_name": "My Security Key"
}
```

#### Verify Registration
```http
POST /api/auth/passkeys/verify-registration
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "id": "credential_id",
  "rawId": "base64_raw_id",
  "response": {
    "clientDataJSON": "base64_client_data",
    "attestationObject": "base64_attestation"
  },
  "type": "public-key"
}
```

#### Authentication Challenge
```http
POST /api/auth/passkeys/authentication-challenge
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "operation_context": "deployment_confirmation"
}
```

#### Verify Authentication
```http
POST /api/auth/passkeys/verify-authentication
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "id": "credential_id",
  "rawId": "base64_raw_id",
  "response": {
    "clientDataJSON": "base64_client_data",
    "authenticatorData": "base64_authenticator_data",
    "signature": "base64_signature",
    "userHandle": "base64_user_handle"
  },
  "type": "public-key",
  "operation_context": "deployment_confirmation"
}
```

## 💻 Frontend Integration

### Basic Usage

```javascript
// Import the utilities
import { confirmWithPassKey, authenticateWithPassKey, hasPassKeys } from '/src/js/passkey-utils.js';

// Check if user has PassKeys
const userHasPassKeys = await hasPassKeys();

if (userHasPassKeys) {
  // Show confirmation dialog with PassKey authentication
  const confirmed = await confirmWithPassKey(
    'Confirm this deployment with your PassKey',
    'deployment_confirmation'
  );

  if (confirmed) {
    // User authenticated - proceed with secure operation
    await deployService();
  }
} else {
  // Fallback to standard confirmation
  const confirmed = confirm('Confirm this deployment?');
  if (confirmed) await deployService();
}
```

### Advanced Usage

```javascript
// Headless authentication (no UI)
try {
  const result = await authenticateWithPassKey('resource_deletion');
  console.log('Authentication result:', result);

  // Proceed with operation
  await deleteResource();

} catch (error) {
  console.error('Authentication failed:', error.message);
  // Handle authentication failure
}
```

### Profile Page Integration

The profile page (`/profile`) includes complete PassKey management:

- **PassKey Registration**: One-click registration with device selection
- **PassKey Management**: View, rename, and delete registered keys
- **Test Authentication**: Demonstration of secure confirmation flow
- **Connected Accounts**: OAuth provider management
- **Authentication Sessions**: View active and past sessions

## 🧪 Testing

### Manual Testing Requirements

⚠️ **Important**: Full PassKey testing requires manual interaction with authenticator devices.

#### Desktop Testing
1. **Hardware Keys** (YubiKey, etc.)
   - Insert hardware key when prompted
   - Touch/activate the key for authentication

2. **Platform Authenticators**
   - Windows Hello (fingerprint/face/PIN)
   - macOS Touch ID
   - Chrome/Edge built-in authenticators

#### Mobile Testing
1. **Cross-Device Authentication**
   - **QR Code Scanning Required**: When testing from desktop, mobile PassKey authentication may require QR code scanning
   - Use your phone's camera to scan authentication QR codes
   - Follow device prompts for biometric authentication

2. **Native Mobile**
   - Face ID/Touch ID on iOS
   - Fingerprint/Face unlock on Android

### Test Scenarios

#### 1. PassKey Registration
```bash
# Navigate to profile page
curl -X GET https://your-domain.com/profile \
  -H "Authorization: Bearer <jwt_token>"

# Test registration flow in browser
# - Click "Add PassKey"
# - Follow browser prompts
# - Verify PassKey appears in list
```

#### 2. Authentication Testing
```bash
# Test the authentication button on profile page
# - Click "Test Authentication"
# - Complete PassKey authentication
# - Verify success notification
```

#### 3. Secure Confirmation Integration
```javascript
// Add to any page requiring secure confirmation
document.getElementById('secure-action').addEventListener('click', async () => {
  const confirmed = await confirmWithPassKey(
    'This action requires PassKey verification',
    'secure_action_test'
  );

  if (confirmed) {
    alert('Action confirmed with PassKey!');
  }
});
```

### Automated Testing

```python
# Backend API tests
def test_passkey_registration_challenge():
    response = client.post("/api/auth/passkeys/registration-challenge",
                          headers=auth_headers,
                          json={"passkey_name": "Test Key"})
    assert response.status_code == 200
    assert "challenge" in response.json()

def test_passkey_authentication_challenge():
    response = client.post("/api/auth/passkeys/authentication-challenge",
                          headers=auth_headers,
                          json={"operation_context": "test"})
    assert response.status_code == 200
    assert "allowCredentials" in response.json()
```

## 🔒 Security Considerations

### Production Deployment

1. **HTTPS Required**: WebAuthn only works over HTTPS
2. **Proper RPID**: Set correct relying party identifier
3. **Origin Validation**: Ensure proper origin checking
4. **Challenge Entropy**: Use cryptographically secure random challenges
5. **Audit Logging**: Enable comprehensive audit trails

### Configuration

```bash
# Required environment variables
DOMAIN=your-production-domain.com
DATABASE_URL=postgresql://secure-connection
AUTH_MODE=jwt

# Optional security enhancements
PASSKEY_CHALLENGE_TIMEOUT=60000
PASSKEY_REQUIRE_USER_VERIFICATION=true
AUDIT_LOG_RETENTION_DAYS=90
```

## 📖 API Reference

### JavaScript Utilities

#### `confirmWithPassKey(message, operationContext, options)`
- **Purpose**: Show modal confirmation dialog with PassKey authentication
- **Parameters**:
  - `message` (string): Confirmation message to display
  - `operationContext` (string): Context identifier for audit logging
  - `options` (object): Optional configuration
- **Returns**: Promise<boolean> - true if authenticated, false if cancelled
- **Example**:
  ```javascript
  const confirmed = await confirmWithPassKey(
    'Delete this resource permanently?',
    'resource_deletion'
  );
  ```

#### `authenticateWithPassKey(operationContext)`
- **Purpose**: Headless PassKey authentication without UI
- **Parameters**:
  - `operationContext` (string): Context identifier for audit logging
- **Returns**: Promise<object> - authentication result object
- **Example**:
  ```javascript
  try {
    const result = await authenticateWithPassKey('api_access');
    // Use result.authenticated_at, result.passkey_name, etc.
  } catch (error) {
    // Handle authentication failure
  }
  ```

#### `hasPassKeys()`
- **Purpose**: Check if user has registered PassKeys
- **Returns**: Promise<boolean> - true if user has PassKeys
- **Example**:
  ```javascript
  if (await hasPassKeys()) {
    // Show PassKey options
  } else {
    // Show registration prompt
  }
  ```

## 🎯 Use Cases

### Deployment Confirmations
```javascript
async function deployService(serviceId) {
  const confirmed = await confirmWithPassKey(
    `Deploy service ${serviceId} to production?`,
    'service_deployment'
  );

  if (confirmed) {
    await fetch(`/api/services/${serviceId}/deploy`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
  }
}
```

### Resource Deletion
```javascript
async function deleteResource(resourceId) {
  const confirmed = await confirmWithPassKey(
    'This action cannot be undone. Delete this resource?',
    'resource_deletion'
  );

  if (confirmed) {
    await fetch(`/api/resources/${resourceId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    });
  }
}
```

### Administrative Actions
```javascript
async function modifyUserRole(userId, newRole) {
  const confirmed = await confirmWithPassKey(
    `Change user role to ${newRole}?`,
    'user_role_modification'
  );

  if (confirmed) {
    await fetch(`/api/users/${userId}/role`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ role: newRole })
    });
  }
}
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "WebAuthn not supported"
- **Solution**: Use HTTPS and modern browser
- **Check**: Chrome 67+, Firefox 60+, Safari 14+

#### 2. "No active PassKeys found"
- **Solution**: Register a PassKey first via profile page
- **Check**: Database connectivity and user authentication

#### 3. "Invalid origin"
- **Solution**: Ensure DOMAIN environment variable matches actual domain
- **Check**: RPID configuration in challenge endpoints

#### 4. "Authentication timeout"
- **Solution**: Complete PassKey prompt within timeout period
- **Check**: Browser permissions and authenticator connectivity

#### 5. Cross-Device Authentication Issues
- **Solution**: Use QR code scanning for mobile authentication
- **Note**: Some flows require manual QR code scanning with mobile device

### Debug Mode

```javascript
// Enable debug logging
window.localStorage.setItem('passkey_debug', 'true');

// Check console for detailed logs
console.log('PassKey utilities loaded');
```

## 📚 Resources

- [WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [MDN WebAuthn Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)
- [FIDO Alliance Resources](https://fidoalliance.org/developers/)
- [Chrome WebAuthn Developer Guide](https://developer.chrome.com/docs/extensions/reference/webAuthenticationAPI/)

## 🤝 Contributing

When extending the PassKey system:

1. **Maintain Security Standards**: Follow WebAuthn best practices
2. **Add Audit Logging**: Log all authentication events
3. **Handle Errors Gracefully**: Provide clear user feedback
4. **Test Thoroughly**: Include both automated and manual testing
5. **Document Changes**: Update this guide with new features

## 📄 License

This PassKey implementation is part of the Service Collection Management webapp and follows the same licensing terms as the parent project.

---

**Note**: This implementation provides enterprise-grade PassKey authentication suitable for production use. All security best practices have been implemented including proper challenge generation, replay protection, and comprehensive audit logging.