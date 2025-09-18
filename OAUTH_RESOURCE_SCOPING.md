# OAuth 2.0 Resource Scoping for Vultr MCP

## Overview

This document outlines OAuth-native approaches to resource-level access control that are more standards-compliant than custom broker patterns.

## OAuth 2.0 Resource Scoping Patterns

### 1. Granular Scopes (RFC 6749 + Best Practices)

**Pattern**: `resource-type:resource-id:permission`

```
Scope Examples:
vultr:dns:supported.systems:read
vultr:dns:supported.systems:write  
vultr:dns:*:read                           # All domains, read-only
vultr:instance:server-123:manage
vultr:instance:production-*:restart        # Production servers only
vultr:firewall:web-tier:configure
vultr:billing:*:read
vultr:api-keys:*:none                      # Explicitly forbidden
```

**Keycloak Configuration**:
```json
{
  "clientScopes": [
    {
      "name": "vultr-dns-read",
      "description": "Read access to DNS domains",
      "protocol": "openid-connect",
      "attributes": {
        "include.in.token.scope": "true"
      }
    },
    {
      "name": "vultr-dns-write", 
      "description": "Write access to DNS domains",
      "protocol": "openid-connect"
    }
  ]
}
```

### 2. Audience-Based Resource Servers (RFC 8693)

**Pattern**: Separate audience for each service area

```json
JWT Token:
{
  "iss": "https://auth.l.inspect.systems",
  "aud": ["vultr-dns", "vultr-compute", "vultr-storage"],
  "scope": "dns:write compute:read storage:read",
  "azp": "mcp-vultr-server",
  "resource_access": {
    "vultr-dns": {
      "domains": ["supported.systems", "inspect.systems"],
      "permissions": ["read", "write", "delete_records"]
    },
    "vultr-compute": {
      "instances": ["server-123", "production-*"],
      "permissions": ["read", "restart", "stop"]
    }
  }
}
```

### 3. Claims-Based Authorization (RECOMMENDED)

**Pattern**: Custom claims with resource mappings

```json
JWT Token Claims:
{
  "iss": "https://auth.l.inspect.systems",
  "aud": "vultr-api",
  "sub": "ryan@supported.systems",
  "scope": "vultr:api",
  
  // Standard claims
  "preferred_username": "ryan",
  "email": "ryan@supported.systems",
  "realm_access": {
    "roles": ["vultr-manager"]
  },
  
  // Custom resource claims
  "vultr_resources": {
    "dns": {
      "domains": [
        {
          "domain": "supported.systems",
          "permissions": ["read", "write", "delete_records"],
          "restrictions": ["no_domain_delete"]
        },
        {
          "domain": "inspect.systems", 
          "permissions": ["read", "write"]
        }
      ]
    },
    "compute": {
      "instances": [
        {
          "instance_id": "122e067b-4c2f-4ed4-bbc2-fb294998f06f",
          "label": "ssh.supported.tech",
          "permissions": ["read", "start", "stop", "restart"],
          "restrictions": ["no_delete", "no_reinstall"]
        }
      ],
      "instance_patterns": [
        {
          "pattern": "production-*",
          "permissions": ["read", "restart"],
          "approval_required": ["stop", "delete"]
        }
      ]
    },
    "global_restrictions": [
      "no_api_key_creation",
      "no_billing_changes",
      "no_user_management"
    ]
  },
  
  // API key from user profile
  "vultr_api_key": "ABCDEF123456...",
  
  // Audit context
  "session_id": "sess_abc123",
  "client_ip": "192.168.1.100"
}
```

## Implementation Approaches

### Option 1: Enhanced Scopes (Simple)

**Keycloak Setup**:
1. Define granular client scopes
2. Map user roles to scope assignments
3. Include resource IDs in scope values

**MCP Server Changes**:
```python
class OAuthResourceValidator:
    def validate_operation(self, token_scopes: List[str], operation: str, resource_id: str) -> bool:
        required_scope = f"vultr:{operation}:{resource_id}"
        wildcard_scope = f"vultr:{operation}:*"
        
        return required_scope in token_scopes or wildcard_scope in token_scopes

# Usage
scopes = ["vultr:dns:supported.systems:write", "vultr:instance:*:read"]
validator = OAuthResourceValidator()
can_create_record = validator.validate_operation(scopes, "dns", "supported.systems")
```

### Option 2: Claims-Based (Recommended)

**Keycloak Protocol Mappers**:
```json
{
  "name": "vultr-resource-claims",
  "protocol": "openid-connect", 
  "protocolMapper": "oidc-usermodel-attribute-mapper",
  "config": {
    "user.attribute": "vultr_resources",
    "claim.name": "vultr_resources", 
    "jsonType.label": "JSON",
    "access.token.claim": "true"
  }
}
```

**User Attribute (JSON)**:
```json
{
  "dns": {
    "allowed_domains": ["supported.systems", "inspect.systems"],
    "forbidden_operations": ["delete_domain"]
  },
  "compute": {
    "allowed_instances": ["server-123", "production-*"],
    "forbidden_operations": ["delete_instance", "create_api_key"]
  }
}
```

**MCP Implementation**:
```python
class ClaimsBasedAuthorizer:
    def __init__(self, jwt_claims: Dict[str, Any]):
        self.vultr_resources = jwt_claims.get('vultr_resources', {})
    
    def can_access_domain(self, domain: str, operation: str) -> bool:
        dns_config = self.vultr_resources.get('dns', {})
        
        # Check allowed domains
        allowed_domains = dns_config.get('allowed_domains', [])
        if allowed_domains and domain not in allowed_domains:
            return False
        
        # Check forbidden operations
        forbidden_ops = dns_config.get('forbidden_operations', [])
        if operation in forbidden_ops:
            return False
            
        return True
    
    def can_access_instance(self, instance_id: str, operation: str) -> bool:
        compute_config = self.vultr_resources.get('compute', {})
        
        # Check patterns and explicit IDs
        allowed_instances = compute_config.get('allowed_instances', [])
        for pattern in allowed_instances:
            if fnmatch.fnmatch(instance_id, pattern):
                break
        else:
            return False  # No matching pattern
        
        # Check operation restrictions
        forbidden_ops = compute_config.get('forbidden_operations', [])
        return operation not in forbidden_ops
```

### Option 3: Resource Servers with Introspection (Enterprise)

**Pattern**: Each Vultr service area as separate OAuth resource server

```python
class VultrResourceServer:
    def __init__(self, service_type: str, introspection_endpoint: str):
        self.service_type = service_type  # "dns", "compute", etc.
        self.introspection_endpoint = introspection_endpoint
    
    async def validate_token(self, access_token: str, resource_id: str, operation: str) -> bool:
        # RFC 7662 Token Introspection
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.introspection_endpoint,
                data={
                    "token": access_token,
                    "resource": f"vultr:{self.service_type}:{resource_id}",
                    "scope": f"{self.service_type}:{operation}"
                }
            )
            
            introspection = response.json()
            return introspection.get("active", False)
```

## Keycloak Configuration Examples

### User Attributes Setup

**User Profile**:
```json
{
  "username": "ryan",
  "email": "ryan@supported.systems",
  "attributes": {
    "vultr_api_key": ["VULTR123..."],
    "vultr_resources": ["{\"dns\":{\"allowed_domains\":[\"supported.systems\"]}}"]
  }
}
```

### Client Scope Mapping

**Client Configuration**:
```json
{
  "clientId": "mcp-vultr-server",
  "defaultClientScopes": ["profile", "email", "vultr-base"],
  "optionalClientScopes": [
    "vultr-dns-read",
    "vultr-dns-write", 
    "vultr-compute-read",
    "vultr-compute-manage"
  ]
}
```

### Dynamic Scope Assignment

**Role-Based Scope Mapping**:
```javascript
// Keycloak Script Mapper
var vultrRole = user.getRealmRoles().stream()
    .filter(role => role.getName().startsWith('vultr-'))
    .findFirst();

if (vultrRole.isPresent()) {
    var roleName = vultrRole.get().getName();
    var scopes = [];
    
    switch(roleName) {
        case 'vultr-dns-admin':
            scopes = ['vultr:dns:*:write', 'vultr:dns:*:delete'];
            break;
        case 'vultr-dns-editor':
            scopes = ['vultr:dns:*:write'];
            break;
        case 'vultr-dns-viewer':
            scopes = ['vultr:dns:*:read'];
            break;
    }
    
    exports = scopes.join(' ');
}
```

## Comparison: Custom Broker vs OAuth-Native

| Aspect | Custom Broker | OAuth Claims | OAuth Scopes |
|--------|---------------|--------------|--------------|
| **Standards Compliance** | Custom | ✅ High | ✅ High |
| **Keycloak Integration** | Complex | ✅ Native | ✅ Native |
| **Performance** | Extra hop | ✅ Fast | ✅ Fast |
| **Audit Trail** | ✅ Detailed | Token-based | Token-based |
| **Granularity** | ✅ Fine-grained | ✅ Fine-grained | Medium |
| **Complexity** | High | Medium | Low |
| **Vultr API Limitation** | ✅ Addresses | Partial | No |

## Recommended Approach

**Phase 1**: Claims-based authorization with Keycloak custom claims
- Store resource permissions in user attributes
- Include full resource access matrix in JWT tokens
- Validate permissions at MCP tool level

**Phase 2**: Add OAuth introspection for real-time validation
- Implement token introspection for sensitive operations
- Enable real-time permission revocation
- Add approval workflows through Keycloak

**Phase 3**: Hybrid approach with selective brokering
- Use OAuth claims for most operations
- Use API key broker only for high-risk operations
- Maintain audit trail through both systems

This gives you the benefits of OAuth standards compliance while addressing Vultr's API limitations where necessary.