# 🌐 Service Collection Management Webapp

A modern, secure web application for managing Vultr service collections with enterprise-grade authentication and deployment workflows.

## ✨ Key Features

### 🔐 **Advanced Authentication**
- **WebAuthn PassKey Integration** - Hardware security key and biometric authentication
- **OAuth Provider Support** - GitHub, Google, and custom OAuth providers
- **Multi-Factor Authentication** - Optional 2FA with TOTP
- **Session Management** - Complete audit trail of authentication events

### 🚀 **Service Collection Management**
- **Resource Orchestration** - Manage complex multi-service deployments
- **Environment Promotion** - Dev → Staging → Production workflows
- **Cost Tracking** - Real-time cost monitoring and budgets
- **Team Collaboration** - Role-based access control and permissions

### 🛡️ **Security & Compliance**
- **Secure Confirmations** - PassKey authentication for sensitive operations
- **Comprehensive Audit Logging** - Complete activity tracking
- **IP Allowlisting** - Restrict access by IP address
- **Encryption at Rest** - Database and file encryption

### ⚡ **Developer Experience**
- **Hot Reload Development** - Instant code updates
- **Docker Integration** - Containerized development and deployment
- **TypeScript Support** - Type-safe frontend development
- **Modern Stack** - FastAPI, Astro, Alpine.js, Tailwind CSS

## 🏗️ Architecture

```mermaid
graph TB
    A[Frontend - Astro.js] --> B[API Gateway - Caddy]
    B --> C[Backend - FastAPI]
    C --> D[Database - PostgreSQL]
    C --> E[Queue - Procrastinate]
    C --> F[Vultr API]

    G[PassKey Authentication] --> C
    H[OAuth Providers] --> C
    I[Audit Logging] --> D
    J[Session Management] --> D
```

### Technology Stack

- **Frontend**: Astro.js, Alpine.js, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL with Alembic migrations
- **Queue**: Procrastinate for background tasks
- **Authentication**: WebAuthn, OAuth 2.0, JWT
- **Infrastructure**: Docker, Caddy, uv package manager

## 🔐 PassKey Authentication System

This webapp features a complete **WebAuthn PassKey implementation** for securing sensitive operations.

### Quick PassKey Setup

```bash
# 1. Start the application
docker compose up -d

# 2. Navigate to profile page
open https://mcp-vultr.l.supported.systems/profile

# 3. Register a PassKey
# Click "Add PassKey" and follow browser prompts

# 4. Test secure confirmation
# Click "Test Authentication" button
```

### Using PassKey in Your Code

```javascript
import { confirmWithPassKey } from '/src/js/passkey-utils.js';

// Secure any operation with PassKey confirmation
async function deployToProduction() {
  const confirmed = await confirmWithPassKey(
    'Deploy to production environment?',
    'production_deployment'
  );

  if (confirmed) {
    // User authenticated with PassKey - proceed safely
    await performDeployment();
  }
}
```

**📖 Complete PassKey Documentation:**
- [Detailed Implementation Guide](./PASSKEY_IMPLEMENTATION.md)
- [Quick Setup Guide](./QUICK_PASSKEY_SETUP.md)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ with uv
- Modern browser with WebAuthn support

### Installation

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd webapp
   ```

2. **Environment Setup**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Configure key settings
   export DOMAIN=your-domain.com
   export DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/db
   export VULTR_API_KEY=your-vultr-api-key
   ```

3. **Start Services**
   ```bash
   # Start all services
   docker compose up -d

   # Check status
   docker compose ps
   ```

4. **Database Setup**
   ```bash
   # Run migrations
   docker compose exec vultr-backend alembic upgrade head
   ```

5. **Access Application**
   - **Web Interface**: https://your-domain.com
   - **API Documentation**: https://your-domain.com/api/docs
   - **Admin Interface**: https://admin.your-domain.com (with dev profile)

## 🧪 Testing

### PassKey Testing Requirements

⚠️ **Important**: PassKey testing requires manual interaction with authenticator devices.

#### Desktop Testing
- **Hardware Keys**: YubiKey, FIDO2 keys
- **Platform Authenticators**: Windows Hello, macOS Touch ID
- **Browser Authenticators**: Chrome/Edge built-in

#### Mobile Testing
- **Cross-Device Authentication**: May require **QR code scanning**
- **Native Biometrics**: Face ID, Touch ID, Fingerprint

### Running Tests

```bash
# Backend tests
docker compose exec vultr-backend pytest

# Frontend tests
docker compose exec frontend npm test

# E2E tests (requires manual PassKey interaction)
docker compose exec frontend npm run test:e2e
```

## 🔧 Development

### Local Development Setup

```bash
# Install dependencies
uv sync              # Backend
npm install          # Frontend

# Start development servers
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000  # Backend
npm run dev -- --host 0.0.0.0                               # Frontend
```

### Hot Reload Configuration

Development mode provides:
- **Backend Hot Reload**: Automatic FastAPI restart on code changes
- **Frontend Hot Reload**: Instant Astro.js updates
- **Database Persistence**: Data retained between restarts
- **Debug Logging**: Comprehensive development logs

### Project Structure

```
webapp/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── models/         # SQLAlchemy models
│   │   ├── core/           # Core utilities and config
│   │   └── tests/          # Backend tests
│   ├── alembic/            # Database migrations
│   └── pyproject.toml      # Python dependencies
│
├── frontend/               # Astro.js frontend
│   ├── src/
│   │   ├── pages/          # Astro pages
│   │   ├── components/     # Reusable components
│   │   ├── layouts/        # Page layouts
│   │   └── js/             # JavaScript utilities
│   ├── public/             # Static assets
│   └── package.json        # Node dependencies
│
├── docker-compose.yml      # Service orchestration
├── .env                    # Environment configuration
└── docs/                   # Documentation
```

## 🔒 Security Features

### Authentication & Authorization
- **Multi-Provider OAuth**: GitHub, Google, custom providers
- **WebAuthn PassKeys**: Hardware security key support
- **JWT Tokens**: Secure API access tokens
- **Role-Based Access**: Granular permission system
- **Session Management**: Complete authentication audit trail

### Data Protection
- **Encryption at Rest**: Database and sensitive data encryption
- **TLS/HTTPS**: All communications encrypted in transit
- **CORS Protection**: Proper cross-origin resource sharing
- **Rate Limiting**: API abuse prevention
- **IP Allowlisting**: Restrict access by IP ranges

### Audit & Compliance
- **Complete Audit Logging**: All actions tracked and logged
- **PassKey Authentication Logs**: WebAuthn operation tracking
- **Session Monitoring**: Active session management
- **Failed Login Tracking**: Brute force attack protection

## 📊 Monitoring & Observability

### Health Checks
```bash
# Application health
curl https://your-domain.com/api/health

# Database connectivity
curl https://your-domain.com/api/health/db

# External service status
curl https://your-domain.com/api/health/vultr
```

### Metrics & Logging
- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: User activity, resource usage, costs
- **Security Metrics**: Authentication events, failed logins
- **Infrastructure Metrics**: Database performance, queue depth

### Log Aggregation
```bash
# View application logs
docker compose logs -f vultr-backend

# View all service logs
docker compose logs -f

# Filter by service
docker compose logs -f postgres
```

## 🚢 Deployment

### Production Deployment

1. **Environment Configuration**
   ```bash
   # Production environment variables
   export ENVIRONMENT=production
   export DEV_MODE=false
   export DATABASE_URL=postgresql://prod-connection
   export DOMAIN=your-production-domain.com
   ```

2. **SSL/TLS Setup**
   ```bash
   # Caddy automatically handles Let's Encrypt certificates
   # Ensure DNS points to your server
   ```

3. **Database Migration**
   ```bash
   # Run production migrations
   docker compose exec vultr-backend alembic upgrade head
   ```

4. **Scale Services**
   ```bash
   # Scale backend instances
   docker compose up -d --scale vultr-backend=3
   ```

### Container Registry
```bash
# Build and push images
docker compose build
docker tag webapp-backend your-registry/webapp-backend:latest
docker push your-registry/webapp-backend:latest
```

## 🤝 Contributing

### Development Workflow

1. **Feature Development**
   ```bash
   # Create feature branch
   git checkout -b feature/passkey-enhancements

   # Make changes with hot reload
   # Test locally with PassKey hardware

   # Commit with descriptive message
   git commit -m "feat: enhance PassKey cross-device authentication"
   ```

2. **Testing Requirements**
   - Unit tests for all new functionality
   - Integration tests for API endpoints
   - Manual PassKey testing with hardware devices
   - Cross-browser compatibility testing

3. **Code Quality**
   - Black formatting for Python code
   - ESLint/Prettier for JavaScript code
   - Type hints for all Python functions
   - Comprehensive docstrings and comments

### Security Considerations

- **Never commit secrets** to version control
- **Test all authentication flows** thoroughly
- **Validate all user inputs** on backend
- **Follow OWASP guidelines** for web security
- **Use PassKey authentication** for sensitive operations

## 📞 Support

### Documentation
- [PassKey Implementation Guide](./PASSKEY_IMPLEMENTATION.md)
- [Quick PassKey Setup](./QUICK_PASSKEY_SETUP.md)
- [API Documentation](https://your-domain.com/api/docs)
- [Development Guide](./docs/DEVELOPMENT.md)

### Troubleshooting
- **PassKey Issues**: Check browser support and HTTPS configuration
- **Authentication Problems**: Verify OAuth provider settings
- **Database Issues**: Check connection strings and migrations
- **Container Problems**: Review Docker logs and resource limits

### Getting Help
- Create issues in the repository for bugs
- Use discussions for questions and feature requests
- Check existing issues for common problems
- Review logs for detailed error information

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🎉 Features Highlight

### 🔐 **Enterprise-Grade PassKey Authentication**
- Complete WebAuthn 2.0 implementation
- Hardware security key support (YubiKey, etc.)
- Platform authenticator integration (Touch ID, Windows Hello)
- Cross-device authentication with QR code support
- Comprehensive audit logging and session management

### 🚀 **Modern Development Stack**
- FastAPI with async/await patterns
- Astro.js with Alpine.js reactivity
- Tailwind CSS for beautiful UI
- Docker containerization with hot reload
- PostgreSQL with efficient migrations

### 🛡️ **Security First**
- Multiple authentication providers
- Role-based access control
- IP allowlisting capabilities
- Complete audit trail
- Encryption at rest and in transit

**Ready to secure your application with PassKeys? Get started with our [Quick Setup Guide](./QUICK_PASSKEY_SETUP.md)!**