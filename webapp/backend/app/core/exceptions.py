"""Custom exceptions for the Service Collection webapp."""

from typing import Optional, Dict, Any


class ServiceCollectionException(Exception):
    """Base exception for Service Collection operations."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "service_collection_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(ServiceCollectionException):
    """Authentication related errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="authentication_error",
            details=details
        )


class AuthorizationError(ServiceCollectionException):
    """Authorization related errors."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="authorization_error",
            details=details
        )


class ValidationError(ServiceCollectionException):
    """Validation related errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            status_code=400,
            error_code="validation_error",
            details=error_details
        )


class ResourceNotFoundError(ServiceCollectionException):
    """Resource not found errors."""
    
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            status_code=404,
            error_code="resource_not_found",
            details=details or {"resource_type": resource_type, "resource_id": resource_id}
        )


class ConflictError(ServiceCollectionException):
    """Resource conflict errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="conflict_error",
            details=details
        )


class VultrAPIError(ServiceCollectionException):
    """Vultr API related errors."""
    
    def __init__(
        self,
        message: str,
        vultr_status_code: Optional[int] = None,
        vultr_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        if vultr_status_code:
            error_details["vultr_status_code"] = vultr_status_code
        if vultr_error_code:
            error_details["vultr_error_code"] = vultr_error_code
        
        super().__init__(
            message=message,
            status_code=502,  # Bad Gateway for external API errors
            error_code="vultr_api_error",
            details=error_details
        )


class WorkflowError(ServiceCollectionException):
    """Workflow operation errors."""
    
    def __init__(self, message: str, operation_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if operation_id:
            error_details["operation_id"] = operation_id
        
        super().__init__(
            message=message,
            status_code=422,
            error_code="workflow_error",
            details=error_details
        )


class RateLimitError(ServiceCollectionException):
    """Rate limiting errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            status_code=429,
            error_code="rate_limit_error",
            details=details
        )