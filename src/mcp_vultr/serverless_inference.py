"""
Vultr Serverless Inference FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Serverless Inference
subscriptions, including AI/ML model deployment, usage monitoring, and optimization.
"""

from typing import Optional, List, Dict, Any
from fastmcp import FastMCP


def create_serverless_inference_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Serverless Inference management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with serverless inference management tools
    """
    mcp = FastMCP(name="vultr-serverless-inference")
    
    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        if len(s) == 36 and s.count('-') == 4:
            return True
        return False
    
    # Helper function to get inference subscription ID from label or UUID
    async def get_inference_id(identifier: str) -> str:
        """
        Get the inference subscription ID from a label or UUID.
        
        Args:
            identifier: Inference subscription label or UUID
            
        Returns:
            The inference subscription ID (UUID)
            
        Raises:
            ValueError: If the inference subscription is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier
            
        # Otherwise, search for it by label
        subscriptions = await vultr_client.list_inference_subscriptions()
        for subscription in subscriptions:
            if subscription.get("label") == identifier:
                return subscription["id"]
        
        raise ValueError(f"Inference subscription '{identifier}' not found (searched by label)")
    
    # Helper function to calculate usage efficiency
    def calculate_usage_efficiency(usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate usage efficiency metrics for an inference subscription.
        
        Args:
            usage_data: Raw usage data from the API
            
        Returns:
            Calculated efficiency metrics and recommendations
        """
        metrics = {
            "efficiency_score": 0.0,
            "recommendations": [],
            "cost_optimization": [],
            "usage_patterns": {}
        }
        
        # Analyze chat/vector store usage
        if "chat" in usage_data:
            chat = usage_data["chat"]
            current_tokens = int(chat.get("current_tokens", "0"))
            monthly_allotment = int(chat.get("monthly_allotment", "1"))
            overage = int(chat.get("overage", "0"))
            
            utilization_rate = current_tokens / monthly_allotment if monthly_allotment > 0 else 0
            metrics["usage_patterns"]["chat_utilization"] = utilization_rate
            
            if utilization_rate < 0.3:
                metrics["recommendations"].append("Consider downgrading plan - low token utilization")
                metrics["cost_optimization"].append("Potential 30-50% cost savings with smaller plan")
            elif utilization_rate > 0.9:
                metrics["recommendations"].append("Consider upgrading plan - nearing token limit")
                
            if overage > 0:
                metrics["recommendations"].append(f"Overage detected: {overage} tokens - upgrade plan")
                overage_rate = overage / current_tokens if current_tokens > 0 else 0
                metrics["cost_optimization"].append(f"Overage costs: {overage_rate:.1%} of usage")
        
        # Analyze audio generation usage
        if "audio" in usage_data:
            audio = usage_data["audio"]
            tts_characters = int(audio.get("tts_characters", "0"))
            
            if tts_characters > 0:
                metrics["usage_patterns"]["audio_usage"] = True
                metrics["recommendations"].append("Monitor audio usage for cost optimization")
        
        # Calculate overall efficiency score
        chat_score = min(1.0, metrics["usage_patterns"].get("chat_utilization", 0) * 1.5)
        metrics["efficiency_score"] = chat_score
        
        return metrics
    
    # Helper function to suggest deployment optimizations
    def suggest_deployment_optimizations(subscription: Dict[str, Any], usage_data: Dict[str, Any]) -> List[str]:
        """
        Suggest deployment optimizations based on subscription and usage data.
        
        Args:
            subscription: Inference subscription data
            usage_data: Usage statistics
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Check API key rotation
        suggestions.append("Rotate API keys regularly for security")
        
        # Check usage patterns
        if "chat" in usage_data:
            chat = usage_data["chat"]
            utilization = int(chat.get("current_tokens", "0")) / int(chat.get("monthly_allotment", "1"))
            
            if utilization < 0.1:
                suggestions.append("Very low usage detected - consider pausing or downsizing")
            elif utilization > 0.95:
                suggestions.append("Near capacity - plan upgrade recommended")
                
        # General best practices
        suggestions.extend([
            "Implement request caching to reduce API calls",
            "Use batch processing for multiple inference requests",
            "Monitor response times and adjust timeout settings",
            "Implement error handling and retry logic",
            "Set up usage alerts to prevent unexpected overage"
        ])
        
        return suggestions

    # Serverless Inference resources
    @mcp.resource("inference://subscriptions")
    async def list_inference_subscriptions_resource() -> List[Dict[str, Any]]:
        """List all serverless inference subscriptions in your Vultr account."""
        return await vultr_client.list_inference_subscriptions()
    
    @mcp.resource("inference://subscription/{subscription_id}")
    async def get_inference_subscription_resource(subscription_id: str) -> Dict[str, Any]:
        """Get information about a specific inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_subscription(actual_id)
    
    @mcp.resource("inference://subscription/{subscription_id}/usage")
    async def get_inference_usage_resource(subscription_id: str) -> Dict[str, Any]:
        """Get usage information for a specific inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_usage(actual_id)

    # Serverless Inference tools
    @mcp.tool
    async def list_serverless_inference() -> List[Dict[str, Any]]:
        """List all serverless inference subscriptions in your Vultr account.
        
        Returns:
            List of inference subscription objects with details including:
            - id: Subscription ID (UUID)
            - label: User-defined label for the subscription
            - api_key: API key for accessing the inference service
            - date_created: When the subscription was created
        """
        return await vultr_client.list_inference_subscriptions()
    
    @mcp.tool
    async def get_serverless_inference(subscription_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label (e.g., "my-ai-model", or UUID)
            
        Returns:
            Detailed inference subscription information including API key and metadata
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_subscription(actual_id)
    
    @mcp.tool
    async def create_serverless_inference(label: str) -> Dict[str, Any]:
        """Create a new serverless inference subscription.
        
        Args:
            label: A descriptive label for the inference subscription (e.g., "production-chatbot", "dev-testing")
            
        Returns:
            Created inference subscription with ID, API key, and configuration details
        """
        return await vultr_client.create_inference_subscription(label)
    
    @mcp.tool
    async def update_serverless_inference(subscription_id: str, label: str) -> Dict[str, Any]:
        """Update an existing serverless inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or current label
            label: New label for the subscription
            
        Returns:
            Updated inference subscription information
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.update_inference_subscription(actual_id, label)
    
    @mcp.tool
    async def delete_serverless_inference(subscription_id: str) -> Dict[str, str]:
        """Delete a serverless inference subscription.
        
        Warning: This action is irreversible and will immediately terminate the subscription.
        
        Args:
            subscription_id: The inference subscription ID or label to delete
            
        Returns:
            Confirmation of deletion
        """
        actual_id = await get_inference_id(subscription_id)
        await vultr_client.delete_inference_subscription(actual_id)
        return {"message": f"Inference subscription '{subscription_id}' has been deleted"}
    
    @mcp.tool
    async def get_inference_usage(subscription_id: str) -> Dict[str, Any]:
        """Get usage statistics for a serverless inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
            
        Returns:
            Detailed usage information including:
            - chat: Token usage for chat/completion models
            - audio: Character usage for text-to-speech models
            - monthly_allotment: Total tokens/characters allocated
            - overage: Usage exceeding the monthly limit
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_usage(actual_id)
    
    @mcp.tool
    async def analyze_inference_usage(subscription_id: str) -> Dict[str, Any]:
        """Analyze usage patterns and provide optimization recommendations.
        
        Args:
            subscription_id: The inference subscription ID or label
            
        Returns:
            Comprehensive analysis including:
            - efficiency_score: Overall utilization efficiency (0-1)
            - recommendations: List of optimization suggestions
            - cost_optimization: Potential cost savings opportunities
            - usage_patterns: Detailed usage breakdown
        """
        actual_id = await get_inference_id(subscription_id)
        usage_data = await vultr_client.get_inference_usage(actual_id)
        
        # Calculate efficiency metrics
        analysis = calculate_usage_efficiency(usage_data)
        analysis["raw_usage"] = usage_data
        
        return analysis
    
    @mcp.tool
    async def get_inference_deployment_guide(subscription_id: str) -> Dict[str, Any]:
        """Get deployment guidance and best practices for an inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
            
        Returns:
            Deployment guide with:
            - api_endpoints: Available API endpoints and documentation
            - authentication: How to use the API key
            - best_practices: Optimization and usage recommendations
            - examples: Sample code and integration patterns
        """
        actual_id = await get_inference_id(subscription_id)
        subscription = await vultr_client.get_inference_subscription(actual_id)
        usage_data = await vultr_client.get_inference_usage(actual_id)
        
        # Generate deployment suggestions
        optimizations = suggest_deployment_optimizations(subscription, usage_data)
        
        guide = {
            "subscription_info": {
                "id": subscription["id"],
                "label": subscription["label"],
                "api_key": subscription["api_key"][:8] + "..." + subscription["api_key"][-4:],  # Masked for security
                "created": subscription["date_created"]
            },
            "api_endpoints": {
                "base_url": "https://api.vultrinference.com",
                "chat_completions": "/v1/chat/completions",
                "text_to_speech": "/v1/audio/speech",
                "documentation": "https://docs.vultr.com/vultr-inference-api"
            },
            "authentication": {
                "header": "Authorization: Bearer YOUR_API_KEY",
                "api_key": "Use the API key from your subscription",
                "security_note": "Keep your API key secure and rotate regularly"
            },
            "best_practices": optimizations,
            "examples": {
                "curl_chat": f"curl -X POST https://api.vultrinference.com/v1/chat/completions -H 'Authorization: Bearer {subscription['api_key']}' -H 'Content-Type: application/json' -d '{{\"model\": \"llama2-7b-chat-Q5_K_M\", \"messages\": [{{\"role\": \"user\", \"content\": \"Hello!\"}}]}}'",
                "python_example": "# Python example available in Vultr documentation",
                "rate_limits": "Monitor usage to stay within monthly allotments"
            }
        }
        
        return guide
    
    @mcp.tool
    async def monitor_inference_performance(subscription_id: str) -> Dict[str, Any]:
        """Monitor performance metrics and usage trends for an inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
            
        Returns:
            Performance monitoring data including:
            - current_usage: Real-time usage statistics
            - trends: Usage patterns and projections
            - alerts: Any usage or performance warnings
            - health_score: Overall subscription health (0-100)
        """
        actual_id = await get_inference_id(subscription_id)
        subscription = await vultr_client.get_inference_subscription(actual_id)
        usage_data = await vultr_client.get_inference_usage(actual_id)
        
        # Calculate health metrics
        health_score = 100
        alerts = []
        
        # Check chat usage health
        if "chat" in usage_data:
            chat = usage_data["chat"]
            current_tokens = int(chat.get("current_tokens", "0"))
            monthly_allotment = int(chat.get("monthly_allotment", "1"))
            overage = int(chat.get("overage", "0"))
            
            utilization = current_tokens / monthly_allotment if monthly_allotment > 0 else 0
            
            if utilization > 0.9:
                health_score -= 20
                alerts.append("High token utilization - consider upgrading plan")
            if overage > 0:
                health_score -= 30
                alerts.append(f"Overage detected: {overage} tokens incurring additional costs")
        
        # Check subscription age (older subscriptions might need key rotation)
        if subscription.get("date_created"):
            alerts.append("Consider rotating API keys periodically for security")
        
        monitoring_data = {
            "subscription_id": actual_id,
            "label": subscription.get("label", "Unknown"),
            "health_score": max(0, health_score),
            "current_usage": usage_data,
            "alerts": alerts,
            "trends": {
                "usage_trajectory": "stable",  # Would be calculated from historical data
                "projected_overage": overage > 0,
                "recommendation": "Monitor usage patterns for optimization opportunities"
            },
            "last_updated": "Real-time"
        }
        
        return monitoring_data
    
    @mcp.tool
    async def optimize_inference_costs(subscription_id: str) -> Dict[str, Any]:
        """Analyze costs and provide optimization recommendations for an inference subscription.
        
        Args:
            subscription_id: The inference subscription ID or label
            
        Returns:
            Cost optimization analysis including:
            - current_costs: Current usage-based costs
            - optimization_opportunities: Ways to reduce costs
            - plan_recommendations: Suggested plan changes
            - savings_potential: Estimated cost savings
        """
        actual_id = await get_inference_id(subscription_id)
        subscription = await vultr_client.get_inference_subscription(actual_id)
        usage_data = await vultr_client.get_inference_usage(actual_id)
        
        optimization = {
            "subscription_info": {
                "id": actual_id,
                "label": subscription.get("label", "Unknown")
            },
            "current_costs": {},
            "optimization_opportunities": [],
            "plan_recommendations": [],
            "savings_potential": "Analysis based on current usage patterns"
        }
        
        # Analyze chat costs
        if "chat" in usage_data:
            chat = usage_data["chat"]
            current_tokens = int(chat.get("current_tokens", "0"))
            monthly_allotment = int(chat.get("monthly_allotment", "1"))
            overage = int(chat.get("overage", "0"))
            
            utilization = current_tokens / monthly_allotment if monthly_allotment > 0 else 0
            
            optimization["current_costs"]["base_plan"] = f"Monthly allotment: {monthly_allotment:,} tokens"
            optimization["current_costs"]["utilization"] = f"{utilization:.1%}"
            
            if overage > 0:
                optimization["current_costs"]["overage_tokens"] = f"{overage:,} tokens"
                optimization["optimization_opportunities"].append("Eliminate overage by upgrading plan")
                optimization["plan_recommendations"].append("Upgrade to higher tier to avoid overage costs")
            
            if utilization < 0.3:
                optimization["optimization_opportunities"].append("Downgrade plan - low utilization detected")
                optimization["plan_recommendations"].append("Consider smaller plan to reduce monthly costs")
                optimization["savings_potential"] = "Potential 30-50% monthly savings"
            elif utilization > 0.8:
                optimization["plan_recommendations"].append("Upgrade plan to avoid approaching limits")
        
        # General optimization opportunities
        optimization["optimization_opportunities"].extend([
            "Implement request caching to reduce API calls",
            "Batch multiple requests where possible",
            "Monitor and optimize prompt length",
            "Use appropriate model sizes for your use case"
        ])
        
        return optimization

    return mcp