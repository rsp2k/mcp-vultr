# Vultr API Key Broker Security Architecture

## Overview

This document outlines a security architecture for managing Vultr API keys using an intermediary "API Key Broker" system to mitigate the inherent security risks in Vultr's all-or-nothing API permission model.

## Problem Statement

### Vultr API Security Issues

1. **Overprivileged Keys**: All API keys have full account access
2. **Key Proliferation**: Ephemeral keys can create more keys, leading to privilege escalation
3. **No Resource Scoping**: Keys cannot be limited to specific resources
4. **Audit Challenges**: Direct API access makes tracking difficult
5. **Revocation Issues**: Once distributed, keys are hard to manage centrally

### Why Vultr Designed It This Way

- **Simplicity**: Easier to implement than granular RBAC
- **Legacy**: API predates modern zero-trust security models
- **Customer Convenience**: Many users prefer simple "full access" model
- **Technical Debt**: Retrofitting permissions is expensive

## API Key Broker Solution

### Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌─────────────┐
│    User     │───▶│ OAuth Token  │───▶│  API Key Broker │───▶│ Vultr API   │
│  (Claude)   │    │  (Keycloak)  │    │   (Secure)      │    │ (Limited)   │
└─────────────┘    └──────────────┘    └─────────────────┘    └─────────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │  Audit System   │
                                       │ • Logs          │
                                       │ • Compliance    │
                                       │ • Alerts        │
                                       └─────────────────┘
```

### Components

#### 1. API Key Broker Service

**Core Responsibilities:**
- Store master Vultr API keys securely (HSM/Vault)
- Issue ephemeral keys with limited scope and expiration
- Proxy API calls with permission validation
- Maintain audit logs of all operations

**Key Features:**
```python
class APIKeyBroker:
    def create_ephemeral_key(
        self, 
        user_context: UserContext,
        permissions: List[Permission],
        expiry_hours: int = 24,
        resource_scope: Optional[Dict] = None
    ) -> EphemeralKey
    
    def validate_operation(
        self,
        ephemeral_key: str,
        operation: str,
        resource_id: Optional[str] = None
    ) -> bool
    
    def audit_api_call(
        self,
        user: str,
        operation: str,
        resource: str,
        result: str,
        timestamp: datetime
    ) -> None
```

#### 2. Permission System

**Resource-Scoped Permissions:**
```yaml
permissions:
  dns:
    domains: ["supported.systems", "inspect.systems"]
    operations: ["read", "create_record", "delete_record"]
    restrictions: ["no_domain_delete"]
  
  instances:
    instance_ids: ["122e067b-4c2f-4ed4-bbc2-fb294998f06f"]
    operations: ["read", "start", "stop", "reboot"]
    restrictions: ["no_delete", "no_reinstall"]
  
  global_restrictions:
    - "no_api_key_creation"
    - "no_billing_changes" 
    - "no_user_management"
```

#### 3. Ephemeral Key Management

**Key Lifecycle:**
1. **Creation**: Short-lived keys (1-24 hours) with specific permissions
2. **Usage**: All API calls go through broker for validation
3. **Rotation**: Automatic renewal for ongoing workflows
4. **Expiration**: Automatic cleanup of expired keys
5. **Emergency Revocation**: Immediate revocation capability

#### 4. Audit & Compliance

**Comprehensive Logging:**
- User identity and OAuth context
- Requested operation and target resource
- Permission check results
- API response status and timing
- Key usage patterns and anomalies

## Implementation Plan

### Phase 1: Core Broker Service

1. **Secure Key Storage**:
   - HashiCorp Vault or AWS Secrets Manager
   - Master key rotation capabilities
   - Multi-factor access controls

2. **Permission Engine**:
   - YAML-based permission definitions
   - Resource-scoped access control
   - Operation-level restrictions

3. **API Proxy Layer**:
   - Intercept all Vultr API calls
   - Validate permissions before forwarding
   - Transform responses to hide sensitive data

### Phase 2: OAuth Integration

1. **Enhanced MCP Server**:
   - Replace direct Vultr API calls with broker calls
   - Extract permissions from OAuth token
   - Request ephemeral keys based on user context

2. **Permission Mapping**:
   - Map OAuth roles to Vultr operations
   - Define resource scopes per user/role
   - Implement approval workflows for sensitive operations

### Phase 3: Advanced Features

1. **Workflow Approval System**:
   - Multi-step approval for destructive operations
   - Time-limited approval tokens
   - Audit trail for approvals

2. **Risk Assessment**:
   - Score operations by risk level
   - Require additional authentication for high-risk ops
   - Automated anomaly detection

3. **Compliance Reporting**:
   - SOC2/ISO27001 audit trails
   - Automated compliance checking
   - Risk management dashboards

## Security Benefits

### Risk Mitigation

1. **Privilege Escalation Prevention**: Ephemeral keys cannot create new keys
2. **Resource Isolation**: Users only access authorized resources
3. **Audit Transparency**: Complete trail of who did what when
4. **Emergency Response**: Immediate key revocation capability
5. **Zero Trust**: Never trust, always verify principle

### Operational Benefits

1. **Centralized Management**: Single point for key lifecycle
2. **Automated Compliance**: Built-in audit and reporting
3. **Scalable Security**: Add users without distributing master keys
4. **Incident Response**: Detailed forensics for security events

## Example Usage Flow

### Scenario: DNS Record Creation

1. **User Request**: Claude user wants to create A record for `api.supported.systems`
2. **OAuth Validation**: Keycloak validates user has `dns-manager` role
3. **Permission Check**: Broker verifies user can modify `supported.systems` domain
4. **Ephemeral Key**: Broker creates 1-hour key with DNS-only permissions
5. **API Call**: MCP server uses ephemeral key to create record
6. **Audit Log**: Complete trail: User → OAuth → Broker → Vultr API
7. **Key Cleanup**: Ephemeral key expires automatically

### Scenario: Instance Management

1. **User Request**: Restart production server
2. **Approval Workflow**: High-risk operation requires manager approval
3. **Scoped Access**: Key only allows operations on specific instance
4. **Time Window**: Operation must complete within 30 minutes
5. **Monitoring**: Real-time alerts for production changes
6. **Compliance**: Automated SOX compliance logging

## Implementation Considerations

### Technical Challenges

1. **Latency**: Additional hop adds ~50-100ms per API call
2. **Reliability**: Broker becomes single point of failure
3. **Scale**: Must handle concurrent requests efficiently
4. **Storage**: Audit logs can grow large quickly

### Mitigation Strategies

1. **Caching**: Cache permissions and validation results
2. **High Availability**: Multi-region broker deployment
3. **Performance**: Async processing for non-critical operations
4. **Storage**: Log rotation and archival strategies

### Security Considerations

1. **Broker Security**: Broker itself becomes high-value target
2. **Master Key Protection**: Secure storage and rotation
3. **Network Security**: TLS everywhere, certificate pinning
4. **Monitoring**: Real-time security monitoring and alerting

## Conclusion

The API Key Broker pattern provides a robust solution to Vultr's API security limitations by:

- Adding granular permission control
- Preventing privilege escalation
- Enabling comprehensive auditing
- Supporting compliance requirements
- Maintaining operational flexibility

This architecture transforms Vultr's "all or nothing" security model into a proper zero-trust system suitable for enterprise environments.