"""
Serverless Inference Analysis utilities for Vultr Serverless Inference.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs usage analysis and optimization recommendations locally.
"""

from typing import Any


class ServerlessInferenceAnalyzer:
    """Custom serverless inference analysis functionality for Vultr inference management."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr serverless inference client."""
        self.vultr_client = vultr_client

    async def analyze_usage(self, subscription_id: str) -> dict[str, Any]:
        """Analyze usage patterns and provide optimization recommendations.

        Args:
            subscription_id: The inference subscription ID or label

        Returns:
            Comprehensive analysis with efficiency score and optimization recommendations
        """
        try:
            # Get subscription details and usage statistics
            subscription_info = await self.vultr_client.get_serverless_inference(
                subscription_id
            )
            usage_stats = await self.vultr_client.get_inference_usage(subscription_id)

            analysis = {
                "subscription_id": subscription_info.get("id"),
                "subscription_label": subscription_info.get("label"),
                "api_key": subscription_info.get("api_key"),
                "usage_analysis": {},
                "efficiency_score": 0.0,
                "usage_patterns": {},
                "optimization_recommendations": [],
                "cost_analysis": {},
            }

            # Analyze usage statistics
            chat_usage = usage_stats.get("chat", {})
            audio_usage = usage_stats.get("audio", {})
            monthly_allotment = usage_stats.get("monthly_allotment", {})
            overage = usage_stats.get("overage", {})

            analysis["usage_analysis"] = {
                "chat_tokens_used": chat_usage.get("current_tokens", 0),
                "chat_tokens_limit": monthly_allotment.get("chat_tokens", 0),
                "audio_characters_used": audio_usage.get("current_characters", 0),
                "audio_characters_limit": monthly_allotment.get("audio_characters", 0),
                "overage_charges": overage.get("total_cost", 0.0),
            }

            # Calculate efficiency score
            analysis["efficiency_score"] = self._calculate_efficiency_score(
                analysis["usage_analysis"]
            )

            # Analyze usage patterns
            analysis["usage_patterns"] = self._analyze_usage_patterns(
                analysis["usage_analysis"]
            )

            # Generate optimization recommendations
            analysis["optimization_recommendations"] = (
                self._generate_optimization_recommendations(
                    analysis["usage_analysis"], analysis["efficiency_score"]
                )
            )

            # Perform cost analysis
            analysis["cost_analysis"] = self._perform_cost_analysis(
                analysis["usage_analysis"]
            )

            return analysis

        except Exception as e:
            return {
                "subscription_id": subscription_id,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze inference usage - check subscription access"
                ],
            }

    async def get_deployment_guide(self, subscription_id: str) -> dict[str, Any]:
        """Get deployment guidance and best practices for an inference subscription.

        Args:
            subscription_id: The inference subscription ID or label

        Returns:
            Deployment guide with API endpoints, authentication, and examples
        """
        try:
            # Get subscription details
            subscription_info = await self.vultr_client.get_serverless_inference(
                subscription_id
            )

            guide = {
                "subscription_id": subscription_info.get("id"),
                "subscription_label": subscription_info.get("label"),
                "api_endpoints": {
                    "base_url": "https://api.vultr.com/v2/inference",
                    "chat_completions": "https://api.vultr.com/v2/inference/chat/completions",
                    "audio_synthesis": "https://api.vultr.com/v2/inference/audio/speech",
                },
                "authentication": {
                    "method": "Bearer Token",
                    "api_key": subscription_info.get("api_key"),
                    "header_format": f"Authorization: Bearer {subscription_info.get('api_key')}",
                    "security_note": "Keep API key secure and never expose in client-side code",
                },
                "integration_examples": {},
                "best_practices": [],
                "monitoring_setup": [],
                "error_handling": [],
            }

            # Generate integration examples
            guide["integration_examples"] = self._generate_integration_examples(
                subscription_info.get("api_key")
            )

            # Generate best practices
            guide["best_practices"] = self._generate_deployment_best_practices()

            # Generate monitoring setup guidance
            guide["monitoring_setup"] = self._generate_monitoring_guidance()

            # Generate error handling recommendations
            guide["error_handling"] = self._generate_error_handling_guidance()

            return guide

        except Exception as e:
            return {
                "subscription_id": subscription_id,
                "error": str(e),
                "recommendations": [
                    "Unable to generate deployment guide - check subscription access"
                ],
            }

    async def monitor_performance(self, subscription_id: str) -> dict[str, Any]:
        """Monitor performance metrics and usage trends for an inference subscription.

        Args:
            subscription_id: The inference subscription ID or label

        Returns:
            Performance monitoring data with health score and alerts
        """
        try:
            # Get subscription and usage data
            subscription_info = await self.vultr_client.get_serverless_inference(
                subscription_id
            )
            usage_stats = await self.vultr_client.get_inference_usage(subscription_id)

            monitoring = {
                "subscription_id": subscription_info.get("id"),
                "subscription_label": subscription_info.get("label"),
                "current_usage": {},
                "usage_trends": {},
                "performance_alerts": [],
                "health_score": 0,
                "recommendations": [],
            }

            # Current usage analysis
            chat_usage = usage_stats.get("chat", {})
            audio_usage = usage_stats.get("audio", {})
            monthly_allotment = usage_stats.get("monthly_allotment", {})

            monitoring["current_usage"] = {
                "chat_utilization_percent": self._calculate_utilization(
                    chat_usage.get("current_tokens", 0),
                    monthly_allotment.get("chat_tokens", 1),
                ),
                "audio_utilization_percent": self._calculate_utilization(
                    audio_usage.get("current_characters", 0),
                    monthly_allotment.get("audio_characters", 1),
                ),
                "approaching_limits": [],
            }

            # Check for approaching limits
            chat_util = monitoring["current_usage"]["chat_utilization_percent"]
            audio_util = monitoring["current_usage"]["audio_utilization_percent"]

            if chat_util > 80:
                monitoring["performance_alerts"].append(
                    "Chat token usage is approaching monthly limit"
                )
                monitoring["current_usage"]["approaching_limits"].append("chat_tokens")

            if audio_util > 80:
                monitoring["performance_alerts"].append(
                    "Audio character usage is approaching monthly limit"
                )
                monitoring["current_usage"]["approaching_limits"].append(
                    "audio_characters"
                )

            # Calculate health score
            monitoring["health_score"] = self._calculate_health_score(
                chat_util, audio_util, len(monitoring["performance_alerts"])
            )

            # Generate monitoring recommendations
            monitoring["recommendations"] = self._generate_monitoring_recommendations(
                monitoring["health_score"], chat_util, audio_util
            )

            return monitoring

        except Exception as e:
            return {
                "subscription_id": subscription_id,
                "error": str(e),
                "recommendations": [
                    "Unable to monitor performance - check subscription access"
                ],
            }

    async def optimize_costs(self, subscription_id: str) -> dict[str, Any]:
        """Analyze costs and provide optimization recommendations for an inference subscription.

        Args:
            subscription_id: The inference subscription ID or label

        Returns:
            Cost optimization analysis with savings potential and recommendations
        """
        try:
            # Get subscription and usage data
            subscription_info = await self.vultr_client.get_serverless_inference(
                subscription_id
            )
            usage_stats = await self.vultr_client.get_inference_usage(subscription_id)

            cost_optimization = {
                "subscription_id": subscription_info.get("id"),
                "subscription_label": subscription_info.get("label"),
                "current_costs": {},
                "optimization_opportunities": [],
                "savings_potential": {},
                "plan_recommendations": [],
                "usage_efficiency": {},
            }

            # Analyze current costs
            overage = usage_stats.get("overage", {})
            chat_usage = usage_stats.get("chat", {})
            audio_usage = usage_stats.get("audio", {})
            monthly_allotment = usage_stats.get("monthly_allotment", {})

            cost_optimization["current_costs"] = {
                "base_subscription_cost": 0.0,  # Would need actual pricing
                "overage_charges": overage.get("total_cost", 0.0),
                "chat_overage": overage.get("chat_cost", 0.0),
                "audio_overage": overage.get("audio_cost", 0.0),
            }

            # Analyze usage efficiency
            chat_efficiency = self._calculate_utilization(
                chat_usage.get("current_tokens", 0),
                monthly_allotment.get("chat_tokens", 1),
            )
            audio_efficiency = self._calculate_utilization(
                audio_usage.get("current_characters", 0),
                monthly_allotment.get("audio_characters", 1),
            )

            cost_optimization["usage_efficiency"] = {
                "chat_utilization": chat_efficiency,
                "audio_utilization": audio_efficiency,
                "overall_efficiency": (chat_efficiency + audio_efficiency) / 2,
            }

            # Identify optimization opportunities
            cost_optimization["optimization_opportunities"] = (
                self._identify_cost_optimizations(
                    cost_optimization["current_costs"],
                    cost_optimization["usage_efficiency"],
                )
            )

            # Calculate savings potential
            cost_optimization["savings_potential"] = self._calculate_savings_potential(
                cost_optimization["current_costs"],
                cost_optimization["usage_efficiency"],
            )

            # Generate plan recommendations
            cost_optimization["plan_recommendations"] = (
                self._generate_plan_recommendations(
                    cost_optimization["usage_efficiency"],
                    cost_optimization["current_costs"],
                )
            )

            return cost_optimization

        except Exception as e:
            return {
                "subscription_id": subscription_id,
                "error": str(e),
                "recommendations": [
                    "Unable to optimize costs - check subscription access"
                ],
            }

    def _calculate_efficiency_score(self, usage_analysis: dict[str, Any]) -> float:
        """Calculate efficiency score based on usage patterns."""
        chat_used = usage_analysis.get("chat_tokens_used", 0)
        chat_limit = usage_analysis.get("chat_tokens_limit", 1)
        audio_used = usage_analysis.get("audio_characters_used", 0)
        audio_limit = usage_analysis.get("audio_characters_limit", 1)

        chat_efficiency = min(chat_used / chat_limit, 1.0) if chat_limit > 0 else 0
        audio_efficiency = min(audio_used / audio_limit, 1.0) if audio_limit > 0 else 0

        # Weighted average (assuming chat is more commonly used)
        overall_efficiency = (chat_efficiency * 0.7) + (audio_efficiency * 0.3)

        return round(overall_efficiency, 3)

    def _analyze_usage_patterns(self, usage_analysis: dict[str, Any]) -> dict[str, Any]:
        """Analyze usage patterns to identify trends."""
        chat_utilization = self._calculate_utilization(
            usage_analysis.get("chat_tokens_used", 0),
            usage_analysis.get("chat_tokens_limit", 1),
        )
        audio_utilization = self._calculate_utilization(
            usage_analysis.get("audio_characters_used", 0),
            usage_analysis.get("audio_characters_limit", 1),
        )

        patterns = {
            "primary_service": "chat"
            if chat_utilization > audio_utilization
            else "audio",
            "usage_distribution": {
                "chat_percentage": chat_utilization,
                "audio_percentage": audio_utilization,
            },
            "usage_category": "light"
            if max(chat_utilization, audio_utilization) < 30
            else "moderate"
            if max(chat_utilization, audio_utilization) < 70
            else "heavy",
        }

        return patterns

    def _generate_optimization_recommendations(
        self, usage_analysis: dict[str, Any], efficiency_score: float
    ) -> list[str]:
        """Generate optimization recommendations based on usage analysis."""
        recommendations = []

        # Efficiency-based recommendations
        if efficiency_score < 0.3:
            recommendations.extend(
                [
                    "Low usage efficiency detected - consider reducing subscription tier",
                    "Monitor usage patterns to identify optimal timing for API calls",
                    "Consider batching requests to improve efficiency",
                ]
            )
        elif efficiency_score > 0.9:
            recommendations.extend(
                [
                    "High usage efficiency - monitor for approaching limits",
                    "Consider upgrading subscription if consistently near limits",
                    "Implement usage monitoring and alerts",
                ]
            )

        # Overage-based recommendations
        overage_charges = usage_analysis.get("overage_charges", 0)
        if overage_charges > 0:
            recommendations.extend(
                [
                    f"Overage charges detected (${overage_charges:.2f}) - consider upgrading plan",
                    "Implement usage tracking to prevent unexpected overages",
                    "Set up alerts when approaching monthly limits",
                ]
            )

        # Service-specific recommendations
        chat_utilization = self._calculate_utilization(
            usage_analysis.get("chat_tokens_used", 0),
            usage_analysis.get("chat_tokens_limit", 1),
        )

        if chat_utilization > 80:
            recommendations.append(
                "Chat token usage is high - optimize prompt length and frequency"
            )

        return recommendations if recommendations else ["Usage patterns appear optimal"]

    def _perform_cost_analysis(self, usage_analysis: dict[str, Any]) -> dict[str, Any]:
        """Perform cost analysis based on usage patterns."""
        overage_charges = usage_analysis.get("overage_charges", 0)

        analysis = {
            "monthly_overage": overage_charges,
            "annual_overage_projection": overage_charges * 12,
            "cost_efficiency": "high"
            if overage_charges == 0
            else "low"
            if overage_charges > 10
            else "moderate",
            "recommendations": [],
        }

        if overage_charges > 0:
            analysis["recommendations"].extend(
                [
                    "Consistent overage charges indicate need for plan upgrade",
                    f"Annual overage projection: ${analysis['annual_overage_projection']:.2f}",
                    "Consider higher-tier subscription to avoid overage fees",
                ]
            )
        else:
            analysis["recommendations"].append(
                "No overage charges - cost efficiency is good"
            )

        return analysis

    def _calculate_utilization(self, used: int, limit: int) -> float:
        """Calculate utilization percentage."""
        if limit <= 0:
            return 0.0
        return round((used / limit) * 100, 2)

    def _calculate_health_score(
        self, chat_util: float, audio_util: float, alert_count: int
    ) -> int:
        """Calculate overall health score."""
        base_score = 100

        # Deduct points for high utilization
        if chat_util > 90:
            base_score -= 30
        elif chat_util > 80:
            base_score -= 15

        if audio_util > 90:
            base_score -= 30
        elif audio_util > 80:
            base_score -= 15

        # Deduct points for alerts
        base_score -= alert_count * 10

        return max(0, base_score)

    def _generate_integration_examples(self, api_key: str) -> dict[str, Any]:
        """Generate integration examples for different programming languages."""
        return {
            "python": {
                "install": "pip install requests",
                "example": f"""
import requests

headers = {{
    'Authorization': 'Bearer {api_key}',
    'Content-Type': 'application/json'
}}

data = {{
    'model': 'vultr-ai-model',
    'messages': [
        {{'role': 'user', 'content': 'Hello, world!'}}
    ]
}}

response = requests.post(
    'https://api.vultr.com/v2/inference/chat/completions',
    headers=headers,
    json=data
)

result = response.json()
print(result['choices'][0]['message']['content'])
""",
            },
            "nodejs": {
                "install": "npm install axios",
                "example": f"""
const axios = require('axios');

const headers = {{
    'Authorization': 'Bearer {api_key}',
    'Content-Type': 'application/json'
}};

const data = {{
    model: 'vultr-ai-model',
    messages: [
        {{ role: 'user', content: 'Hello, world!' }}
    ]
}};

axios.post('https://api.vultr.com/v2/inference/chat/completions', data, {{ headers }})
    .then(response => {{
        console.log(response.data.choices[0].message.content);
    }})
    .catch(error => {{
        console.error('Error:', error);
    }});
""",
            },
            "curl": f"""
curl -X POST https://api.vultr.com/v2/inference/chat/completions \\
  -H "Authorization: Bearer {api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "model": "vultr-ai-model",
    "messages": [
      {{"role": "user", "content": "Hello, world!"}}
    ]
  }}'
""",
        }

    def _generate_deployment_best_practices(self) -> list[str]:
        """Generate deployment best practices."""
        return [
            "Store API keys securely using environment variables or secret management",
            "Implement proper error handling and retry logic with exponential backoff",
            "Monitor usage patterns and set up alerts for approaching limits",
            "Use connection pooling for high-frequency API calls",
            "Implement caching where appropriate to reduce API calls",
            "Consider rate limiting on your application side to prevent overages",
            "Use asynchronous processing for non-real-time inference requests",
            "Implement proper logging for debugging and monitoring",
        ]

    def _generate_monitoring_guidance(self) -> list[str]:
        """Generate monitoring setup guidance."""
        return [
            "Set up daily usage monitoring to track token and character consumption",
            "Implement alerts when usage reaches 80% of monthly limits",
            "Monitor API response times and error rates",
            "Track overage charges and cost trends",
            "Set up dashboards for real-time usage visualization",
            "Implement health checks for your inference endpoints",
            "Monitor for API key security and rotate keys regularly",
        ]

    def _generate_error_handling_guidance(self) -> list[str]:
        """Generate error handling recommendations."""
        return [
            "Implement exponential backoff for rate limit errors (429)",
            "Handle authentication errors (401) by refreshing or validating API keys",
            "Retry transient errors (5xx) with appropriate delays",
            "Validate input data before sending to API to prevent 4xx errors",
            "Implement circuit breaker pattern for sustained API failures",
            "Log all API errors with sufficient context for debugging",
            "Provide graceful degradation when inference API is unavailable",
        ]

    def _generate_monitoring_recommendations(
        self, health_score: int, chat_util: float, audio_util: float
    ) -> list[str]:
        """Generate monitoring recommendations based on health score."""
        recommendations = []

        if health_score < 50:
            recommendations.append(
                "CRITICAL: Low health score - immediate attention required"
            )
        elif health_score < 70:
            recommendations.append("WARNING: Moderate health score - monitor closely")
        else:
            recommendations.append("Health score is good - continue normal monitoring")

        if chat_util > 80 or audio_util > 80:
            recommendations.append(
                "High utilization detected - consider upgrading subscription"
            )

        recommendations.extend(
            [
                "Set up automated monitoring and alerting",
                "Review usage patterns weekly",
                "Monitor for cost optimization opportunities",
            ]
        )

        return recommendations

    def _identify_cost_optimizations(
        self, current_costs: dict[str, Any], usage_efficiency: dict[str, Any]
    ) -> list[str]:
        """Identify cost optimization opportunities."""
        opportunities = []

        if current_costs.get("overage_charges", 0) > 0:
            opportunities.append(
                "Eliminate overage charges by upgrading subscription tier"
            )

        overall_efficiency = usage_efficiency.get("overall_efficiency", 0)
        if overall_efficiency < 50:
            opportunities.append(
                "Low usage efficiency - consider downgrading subscription"
            )
        elif overall_efficiency > 90:
            opportunities.append(
                "High usage efficiency - may need upgrade to avoid overages"
            )

        return (
            opportunities
            if opportunities
            else ["No obvious cost optimization opportunities"]
        )

    def _calculate_savings_potential(
        self, current_costs: dict[str, Any], usage_efficiency: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate potential savings from optimization."""
        overage_charges = current_costs.get("overage_charges", 0)

        return {
            "monthly_overage_elimination": overage_charges,
            "annual_savings_potential": overage_charges * 12,
            "efficiency_improvement_potential": max(
                0, 100 - usage_efficiency.get("overall_efficiency", 0)
            ),
        }

    def _generate_plan_recommendations(
        self, usage_efficiency: dict[str, Any], current_costs: dict[str, Any]
    ) -> list[str]:
        """Generate plan change recommendations."""
        recommendations = []

        overall_efficiency = usage_efficiency.get("overall_efficiency", 0)
        overage_charges = current_costs.get("overage_charges", 0)

        if overage_charges > 0:
            recommendations.append(
                "Consider upgrading to higher-tier plan to eliminate overage charges"
            )
        elif overall_efficiency < 30:
            recommendations.append(
                "Consider downgrading to lower-tier plan due to low usage"
            )
        elif overall_efficiency > 85:
            recommendations.append(
                "Monitor closely - may need upgrade if usage continues to grow"
            )
        else:
            recommendations.append(
                "Current plan appears appropriate for usage patterns"
            )

        return recommendations
