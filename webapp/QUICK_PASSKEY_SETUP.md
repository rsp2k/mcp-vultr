# 🚀 Quick PassKey Setup Guide

Get PassKey authentication running in 5 minutes.

## ⚡ Prerequisites Check

```bash
# Check versions
node --version    # Need 18+
python --version  # Need 3.11+
docker --version  # Need recent version

# Check browser WebAuthn support
# Open browser console and run:
navigator.credentials && window.PublicKeyCredential
# Should return: true
```

## 🏃‍♂️ 5-Minute Setup

### 1. Environment Setup (30 seconds)
```bash
# Ensure .env is configured
grep -E "(DOMAIN|DATABASE_URL)" .env

# Should show:
# DOMAIN=mcp-vultr.l.supported.systems
# DATABASE_URL=postgresql+asyncpg://...
```

### 2. Start Services (2 minutes)
```bash
# Clean start
docker compose down --remove-orphans
docker compose up -d

# Wait for healthy status
docker compose logs vultr-backend --tail 5
# Should show: "Application startup complete"
```

### 3. Database Migration (30 seconds)
```bash
# Create PassKey tables
docker compose exec vultr-backend alembic upgrade head

# Verify tables exist
docker compose exec postgres psql -U service_collections -d service_collections -c "\dt" | grep -E "(passkeys|connected_accounts)"
```

### 4. Test Access (1 minute)
```bash
# Check app is running
curl -I https://mcp-vultr.l.supported.systems
# Should return: HTTP/2 200

# Check API is running
curl -I https://mcp-vultr.l.supported.systems/api/health
# Should return: HTTP/2 200
```

### 5. Verify PassKey System (1 minute)
Open browser and navigate to: `https://mcp-vultr.l.supported.systems/profile`

You should see:
- ✅ Connected Accounts section
- ✅ PassKeys section with "Add PassKey" button
- ✅ Authentication Sessions section

## 🧪 Quick Test

### Test PassKey Registration
1. **Login via GitHub OAuth**
2. **Navigate to Profile page**
3. **Click "Add PassKey"**
4. **Follow browser prompts**
5. **Verify PassKey appears in list**

### Test Authentication
1. **Click "Test Authentication" button** (appears after adding PassKey)
2. **Complete PassKey prompt** (touch hardware key, use biometric, etc.)
3. **See success notification**

⚠️ **Mobile Testing Note**: Cross-device authentication may require **QR code scanning** with your mobile device.

## 🔧 Integration Example

Drop this into any page for secure confirmations:

```javascript
// Add to your page
import { confirmWithPassKey } from '/src/js/passkey-utils.js';

// Use anywhere you need secure confirmation
document.getElementById('dangerous-action').onclick = async () => {
  const confirmed = await confirmWithPassKey(
    'This action requires PassKey verification',
    'dangerous_action_context'
  );

  if (confirmed) {
    // User authenticated with PassKey - proceed
    await performDangerousAction();
  }
};
```

## 🐛 Troubleshooting Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| "WebAuthn not supported" | Use HTTPS and modern browser (Chrome 67+) |
| "No active PassKeys found" | Register a PassKey first in profile page |
| Backend not starting | Check logs: `docker compose logs vultr-backend` |
| Database connection error | Verify PostgreSQL is healthy: `docker compose ps` |
| Authentication timeout | Complete PassKey prompt within 60 seconds |
| QR code needed | Use mobile device camera to scan authentication QR |

## 📱 Mobile Testing Setup

For testing cross-device authentication:

1. **Desktop**: Initiate PassKey authentication
2. **Mobile**:
   - Open camera app
   - Scan QR code when prompted
   - Complete biometric authentication
   - Return to desktop for completion

## ✅ Success Indicators

You'll know the system is working when:

- ✅ PassKey registration completes without errors
- ✅ Test authentication button works
- ✅ Backend logs show "PassKey authentication successful"
- ✅ Audit logs record authentication events
- ✅ User sees success notifications in UI

## 🚨 Common Gotchas

1. **HTTPS Required**: WebAuthn only works over HTTPS
2. **Browser Support**: Use modern browsers (no IE/old Safari)
3. **User Gesture**: PassKey prompts require user interaction (button clicks)
4. **Timeout Handling**: PassKey prompts timeout after 60 seconds
5. **Mobile QR Codes**: Cross-device flows may require QR code scanning

---

🎉 **That's it!** Your PassKey authentication system is ready for secure confirmations throughout your application.

For detailed API reference and advanced configuration, see: [`PASSKEY_IMPLEMENTATION.md`](./PASSKEY_IMPLEMENTATION.md)