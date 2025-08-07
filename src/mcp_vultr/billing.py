"""
Vultr Billing FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr billing and account information.
"""

from typing import List, Dict, Any, Optional
from fastmcp import FastMCP


def create_billing_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr billing management.
    
    Args:
        vultr_client: VultrDNSServer instance
        
    Returns:
        Configured FastMCP instance with billing management tools
    """
    mcp = FastMCP(name="vultr-billing")
    
    @mcp.tool()
    async def get_account_info() -> Dict[str, Any]:
        """
        Get account information including billing details.
        
        Returns:
            Account information and billing details
        """
        return await vultr_client.get_account_info()
    
    @mcp.tool()
    async def get_current_balance() -> Dict[str, Any]:
        """
        Get current account balance and payment information.
        
        Returns:
            Current balance, pending charges, and payment history
        """
        return await vultr_client.get_current_balance()
    
    @mcp.tool()
    async def list_billing_history(
        days: Optional[int] = 30,
        per_page: Optional[int] = 25
    ) -> Dict[str, Any]:
        """
        List billing history for the specified number of days.
        
        Args:
            days: Number of days to include (default: 30)
            per_page: Number of items per page (default: 25)
            
        Returns:
            Billing history with transaction details
        """
        return await vultr_client.list_billing_history(date_range=days, per_page=per_page)
    
    @mcp.tool()
    async def list_invoices(per_page: Optional[int] = 25) -> Dict[str, Any]:
        """
        List all invoices.
        
        Args:
            per_page: Number of items per page (default: 25)
            
        Returns:
            List of invoices with pagination info
        """
        return await vultr_client.list_invoices(per_page=per_page)
    
    @mcp.tool()
    async def get_invoice(invoice_id: str) -> Dict[str, Any]:
        """
        Get details of a specific invoice.
        
        Args:
            invoice_id: The invoice ID
            
        Returns:
            Invoice details including line items
        """
        return await vultr_client.get_invoice(invoice_id)
    
    @mcp.tool()
    async def list_invoice_items(
        invoice_id: str,
        per_page: Optional[int] = 25
    ) -> Dict[str, Any]:
        """
        List items in a specific invoice.
        
        Args:
            invoice_id: The invoice ID
            per_page: Number of items per page (default: 25)
            
        Returns:
            Invoice line items with details
        """
        return await vultr_client.list_invoice_items(invoice_id, per_page=per_page)
    
    @mcp.tool()
    async def get_monthly_usage_summary(year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly usage and cost summary.
        
        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            
        Returns:
            Monthly usage summary with service breakdown
        """
        return await vultr_client.get_monthly_usage_summary(year, month)
    
    @mcp.tool()
    async def get_current_month_summary() -> Dict[str, Any]:
        """
        Get current month usage and cost summary.
        
        Returns:
            Current month usage summary with service breakdown
        """
        from datetime import datetime
        now = datetime.now()
        return await vultr_client.get_monthly_usage_summary(now.year, now.month)
    
    @mcp.tool()
    async def get_last_month_summary() -> Dict[str, Any]:
        """
        Get last month usage and cost summary.
        
        Returns:
            Last month usage summary with service breakdown
        """
        from datetime import datetime, timedelta
        last_month = datetime.now() - timedelta(days=30)
        return await vultr_client.get_monthly_usage_summary(last_month.year, last_month.month)
    
    @mcp.tool()
    async def analyze_spending_trends(months: int = 6) -> Dict[str, Any]:
        """
        Analyze spending trends over the past months.
        
        Args:
            months: Number of months to analyze (default: 6)
            
        Returns:
            Spending analysis with trends and recommendations
        """
        from datetime import datetime, timedelta
        import calendar
        
        current_date = datetime.now()
        monthly_summaries = []
        
        for i in range(months):
            # Calculate the date for each month going backwards
            target_date = current_date.replace(day=1) - timedelta(days=i*30)
            year = target_date.year
            month = target_date.month
            
            try:
                summary = await vultr_client.get_monthly_usage_summary(year, month)
                summary["month_name"] = calendar.month_name[month]
                monthly_summaries.append(summary)
            except Exception:
                # Skip months with no data
                continue
        
        if not monthly_summaries:
            return {"error": "No billing data available for analysis"}
        
        # Calculate trends
        total_costs = [summary["total_cost"] for summary in monthly_summaries]
        average_cost = sum(total_costs) / len(total_costs)
        
        trend = "stable"
        if len(total_costs) >= 2:
            recent_avg = sum(total_costs[:2]) / 2 if len(total_costs) >= 2 else total_costs[0]
            older_avg = sum(total_costs[2:]) / len(total_costs[2:]) if len(total_costs) > 2 else recent_avg
            
            if recent_avg > older_avg * 1.1:
                trend = "increasing"
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
        
        # Service analysis
        all_services = set()
        for summary in monthly_summaries:
            all_services.update(summary.get("service_breakdown", {}).keys())
        
        service_trends = {}
        for service in all_services:
            service_costs = []
            for summary in monthly_summaries:
                cost = summary.get("service_breakdown", {}).get(service, 0)
                service_costs.append(cost)
            
            if service_costs:
                service_trends[service] = {
                    "average_cost": round(sum(service_costs) / len(service_costs), 2),
                    "total_cost": round(sum(service_costs), 2),
                    "latest_cost": service_costs[0] if service_costs else 0
                }
        
        return {
            "analysis_period": f"{months} months",
            "monthly_summaries": monthly_summaries,
            "overall_trend": trend,
            "average_monthly_cost": round(average_cost, 2),
            "highest_month_cost": max(total_costs),
            "lowest_month_cost": min(total_costs),
            "service_analysis": service_trends,
            "recommendations": _generate_cost_recommendations(trend, service_trends, average_cost)
        }
    
    @mcp.tool()
    async def get_cost_breakdown_by_service(days: int = 30) -> Dict[str, Any]:
        """
        Get cost breakdown by service for the specified period.
        
        Args:
            days: Number of days to analyze (default: 30)
            
        Returns:
            Service-wise cost breakdown with percentages
        """
        billing_data = await vultr_client.list_billing_history(date_range=days)
        billing_history = billing_data.get("billing_history", [])
        
        service_costs = {}
        total_cost = 0
        
        for item in billing_history:
            amount = float(item.get("amount", 0))
            total_cost += amount
            
            description = item.get("description", "Unknown")
            service_type = description.split()[0] if description else "Unknown"
            
            if service_type not in service_costs:
                service_costs[service_type] = 0
            service_costs[service_type] += amount
        
        # Calculate percentages
        service_breakdown = {}
        for service, cost in service_costs.items():
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            service_breakdown[service] = {
                "cost": round(cost, 2),
                "percentage": round(percentage, 1)
            }
        
        return {
            "period_days": days,
            "total_cost": round(total_cost, 2),
            "service_breakdown": service_breakdown,
            "transaction_count": len(billing_history)
        }
    
    @mcp.tool()
    async def get_payment_summary() -> Dict[str, Any]:
        """
        Get payment summary and account status.
        
        Returns:
            Payment summary with account status
        """
        account_info = await vultr_client.get_account_info()
        balance_info = await vultr_client.get_current_balance()
        
        return {
            "account_status": "active" if account_info.get("balance", 0) >= 0 else "attention_required",
            "current_balance": balance_info.get("balance", 0),
            "pending_charges": balance_info.get("pending_charges", 0),
            "last_payment": {
                "date": balance_info.get("last_payment_date"),
                "amount": balance_info.get("last_payment_amount")
            },
            "account_email": account_info.get("email"),
            "account_name": account_info.get("name"),
            "billing_email": account_info.get("billing_email")
        }
    
    def _generate_cost_recommendations(trend: str, service_trends: Dict, average_cost: float) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        if trend == "increasing":
            recommendations.append("Your costs are trending upward. Review recent resource usage.")
            
        if average_cost > 100:
            recommendations.append("Consider using reserved instances or committed use discounts.")
            
        # Find most expensive service
        if service_trends:
            most_expensive = max(service_trends.items(), key=lambda x: x[1]["total_cost"])
            recommendations.append(f"Your highest cost service is {most_expensive[0]}. Review optimization opportunities.")
            
        if not recommendations:
            recommendations.append("Your spending appears stable. Continue monitoring for changes.")
            
        return recommendations
    
    return mcp