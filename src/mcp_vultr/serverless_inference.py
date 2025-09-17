"""
Vultr Serverless Inference FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Serverless Inference
subscriptions, including AI/ML model deployment, usage monitoring, and optimization.
"""

from typing import Any

from fastmcp import FastMCP

from .serverless_inference_analyzer import ServerlessInferenceAnalyzer


def create_serverless_inference_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Serverless Inference management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with serverless inference management tools
    """
    mcp = FastMCP(name="vultr-serverless-inference")
    inference_analyzer = ServerlessInferenceAnalyzer(vultr_client)

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

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

        raise ValueError(
            f"Inference subscription '{identifier}' not found (searched by label)"
        )

    # Serverless Inference resources
    @mcp.resource("inference://subscriptions")
    async def list_inference_subscriptions_resource() -> list[dict[str, Any]]:
        """List all serverless inference subscriptions in your Vultr account."""
        return await vultr_client.list_inference_subscriptions()

    @mcp.resource("inference://subscription/{subscription_id}")
    async def get_inference_subscription_resource(
        subscription_id: str,
    ) -> dict[str, Any]:
        """Get information about a specific inference subscription.

        Args:
            subscription_id: The inference subscription ID or label
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_subscription(actual_id)

    @mcp.resource("inference://subscription/{subscription_id}/usage")
    async def get_inference_usage_resource(subscription_id: str) -> dict[str, Any]:
        """Get usage information for a specific inference subscription.

        Args:
            subscription_id: The inference subscription ID or label
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_usage(actual_id)

    # Serverless Inference tools
    @mcp.tool
    async def list_serverless_inference() -> list[dict[str, Any]]:
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
    async def get_serverless_inference(subscription_id: str) -> dict[str, Any]:
        """Get detailed information about a specific inference subscription.

        Args:
            subscription_id: The inference subscription ID or label (e.g., "my-ai-model", or UUID)

        Returns:
            Detailed inference subscription information including API key and metadata
        """
        actual_id = await get_inference_id(subscription_id)
        return await vultr_client.get_inference_subscription(actual_id)

    @mcp.tool
    async def create_serverless_inference(label: str) -> dict[str, Any]:
        """Create a new serverless inference subscription.

        Args:
            label: A descriptive label for the inference subscription (e.g., "production-chatbot", "dev-testing")

        Returns:
            Created inference subscription with ID, API key, and configuration details
        """
        return await vultr_client.create_inference_subscription(label)

    @mcp.tool
    async def update_serverless_inference(
        subscription_id: str, label: str
    ) -> dict[str, Any]:
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
    async def delete_serverless_inference(subscription_id: str) -> dict[str, str]:
        """Delete a serverless inference subscription.

        Warning: This action is irreversible and will immediately terminate the subscription.

        Args:
            subscription_id: The inference subscription ID or label to delete

        Returns:
            Confirmation of deletion
        """
        actual_id = await get_inference_id(subscription_id)
        await vultr_client.delete_inference_subscription(actual_id)
        return {
            "message": f"Inference subscription '{subscription_id}' has been deleted"
        }

    @mcp.tool
    async def get_inference_usage(subscription_id: str) -> dict[str, Any]:
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
    async def analyze_inference_usage(subscription_id: str) -> dict[str, Any]:
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
        return await inference_analyzer.analyze_usage(subscription_id)

    @mcp.tool
    async def get_inference_deployment_guide(subscription_id: str) -> dict[str, Any]:
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
        return await inference_analyzer.get_deployment_guide(subscription_id)

    @mcp.tool
    async def monitor_inference_performance(subscription_id: str) -> dict[str, Any]:
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
        return await inference_analyzer.monitor_performance(subscription_id)

    @mcp.tool
    async def optimize_inference_costs(subscription_id: str) -> dict[str, Any]:
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
        return await inference_analyzer.optimize_costs(subscription_id)

    return mcp
