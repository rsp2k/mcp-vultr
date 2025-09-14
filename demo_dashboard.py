#!/usr/bin/env python3
"""
Demo Dashboard Generator

Creates a beautiful demonstration of the HTML testing dashboard
with sample data to showcase all features and design elements.

This script generates:
1. Sample test results with various scenarios
2. Mock coverage data across modules
3. Performance metrics and trends
4. Historical data simulation
5. Complete dashboard with all themes

Usage:
    python demo_dashboard.py
    # Opens generated dashboard in browser
"""

import json
import random
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from dashboard_generator import DashboardGenerator


class DemoDashboardGenerator(DashboardGenerator):
    """Extended dashboard generator with rich sample data."""
    
    def generate_demo_dashboard(self) -> str:
        """Generate a complete demo dashboard with sample data."""
        print("🎨 Generating demo dashboard with sample data...")
        
        # Generate rich sample data
        demo_data = self.create_demo_data()
        
        # Create enhanced HTML with demo features
        html_content = self.create_demo_html_template(demo_data)
        
        # Write demo dashboard
        dashboard_path = self.reports_dir / "demo_dashboard.html"
        dashboard_path.write_text(html_content, encoding='utf-8')
        
        print(f"✅ Demo dashboard generated: {dashboard_path}")
        print(f"🌐 Open in browser: file://{dashboard_path.absolute()}")
        
        return str(dashboard_path)
    
    def create_demo_data(self) -> Dict[str, Any]:
        """Create comprehensive demo data."""
        return {
            "coverage": self.generate_demo_coverage_data(),
            "tests": self.generate_demo_test_data(),
            "performance": self.generate_demo_performance_data(),
            "historical": self.generate_demo_historical_data(),
            "quality": self.generate_demo_quality_data(),
            "modules": self.generate_demo_module_data(),
            "generated_at": datetime.now().isoformat(),
            "project": "MCP-Vultr Testing Dashboard Demo"
        }
    
    def generate_demo_coverage_data(self) -> Dict[str, Any]:
        """Generate realistic coverage data."""
        return {
            "overall_percentage": 78.3,
            "total_statements": 5306,
            "missing_statements": 1151,
            "covered_statements": 4155,
            "modules": [
                {"name": "src/mcp_vultr/__init__.py", "statements": 8, "missing": 0, "coverage": 100, "status": "excellent"},
                {"name": "src/mcp_vultr/_version.py", "statements": 2, "missing": 0, "coverage": 100, "status": "excellent"},
                {"name": "src/mcp_vultr/cache.py", "statements": 94, "missing": 2, "coverage": 98, "status": "excellent"},
                {"name": "src/mcp_vultr/retry.py", "statements": 49, "missing": 5, "coverage": 90, "status": "excellent"},
                {"name": "src/mcp_vultr/metrics.py", "statements": 124, "missing": 15, "coverage": 88, "status": "good"},
                {"name": "src/mcp_vultr/client.py", "statements": 86, "missing": 12, "coverage": 86, "status": "good"},
                {"name": "src/mcp_vultr/logging.py", "statements": 35, "missing": 5, "coverage": 86, "status": "good"},
                {"name": "src/mcp_vultr/fastmcp_server.py", "statements": 95, "missing": 20, "coverage": 79, "status": "warning"},
                {"name": "src/mcp_vultr/server.py", "statements": 1520, "missing": 340, "coverage": 78, "status": "warning"},
                {"name": "src/mcp_vultr/dns.py", "statements": 71, "missing": 18, "coverage": 75, "status": "warning"},
                {"name": "src/mcp_vultr/cli_main.py", "statements": 74, "missing": 25, "coverage": 66, "status": "critical"},
                {"name": "src/mcp_vultr/tui_app.py", "statements": 245, "missing": 85, "coverage": 65, "status": "critical"},
            ],
            "trends": {
                "last_week": 75.2,
                "last_month": 72.8,
                "change": "+5.5%"
            }
        }
    
    def generate_demo_test_data(self) -> Dict[str, Any]:
        """Generate realistic test result data."""
        return {
            "total": 187,
            "passed": 165,
            "failed": 12,
            "skipped": 10,
            "duration": 89.4,
            "success_rate": 88.2,
            "categories": {
                "unit": {"total": 95, "passed": 88, "failed": 4, "skipped": 3, "duration": 23.1},
                "integration": {"total": 52, "passed": 45, "failed": 5, "skipped": 2, "duration": 45.2},
                "mcp": {"total": 28, "passed": 22, "failed": 2, "skipped": 4, "duration": 18.7},
                "tui": {"total": 12, "passed": 10, "failed": 1, "skipped": 1, "duration": 2.4}
            },
            "recent_failures": [
                {
                    "test": "test_vultr_auth_timeout", 
                    "file": "test_client.py", 
                    "error": "TimeoutError", 
                    "duration": 30.1,
                    "line": 145
                },
                {
                    "test": "test_dns_record_validation", 
                    "file": "test_server.py", 
                    "error": "ValidationError", 
                    "duration": 2.3,
                    "line": 89
                },
                {
                    "test": "test_mcp_server_connection", 
                    "file": "test_mcp_server.py", 
                    "error": "ConnectionError", 
                    "duration": 15.7,
                    "line": 203
                },
                {
                    "test": "test_tui_navigation_keys", 
                    "file": "test_tui_app.py", 
                    "error": "KeyError", 
                    "duration": 1.2,
                    "line": 67
                }
            ],
            "flaky_tests": [
                {"test": "test_api_rate_limiting", "flake_rate": 0.15},
                {"test": "test_concurrent_requests", "flake_rate": 0.08},
                {"test": "test_network_timeout", "flake_rate": 0.12}
            ]
        }
    
    def generate_demo_performance_data(self) -> Dict[str, Any]:
        """Generate performance metrics."""
        return {
            "slowest_tests": [
                {"name": "test_comprehensive_error_handling", "duration": 15.2, "category": "integration"},
                {"name": "test_all_vultr_tools_integration", "duration": 12.8, "category": "mcp"},
                {"name": "test_tui_full_workflow", "duration": 8.9, "category": "tui"},
                {"name": "test_concurrent_api_calls", "duration": 7.4, "category": "integration"},
                {"name": "test_large_dns_zone_import", "duration": 6.1, "category": "unit"},
                {"name": "test_stress_cache_operations", "duration": 4.7, "category": "unit"},
                {"name": "test_memory_leak_detection", "duration": 4.2, "category": "integration"},
                {"name": "test_startup_time_optimization", "duration": 3.8, "category": "unit"}
            ],
            "memory_usage": {
                "peak_mb": 387,
                "average_mb": 245,
                "baseline_mb": 156,
                "gc_collections": 67,
                "memory_growth": "+12%"
            },
            "parallel_efficiency": {
                "workers": 8,
                "speedup_factor": 6.2,
                "load_balance": 0.78,
                "cpu_utilization": 85
            },
            "test_timing_distribution": {
                "fast": {"count": 145, "avg_duration": 0.8, "percentage": 77.5},
                "medium": {"count": 32, "avg_duration": 4.2, "percentage": 17.1},
                "slow": {"count": 10, "avg_duration": 12.1, "percentage": 5.4}
            }
        }
    
    def generate_demo_historical_data(self) -> List[Dict[str, Any]]:
        """Generate historical trend data."""
        historical = []
        base_date = datetime.now()
        
        for i in range(30):
            date = base_date - timedelta(days=i)
            
            # Simulate realistic trends
            coverage_trend = 75 + random.uniform(-5, 8) + (i * 0.1)  # Gradual improvement
            test_count = 180 + random.randint(-5, 10)
            pass_rate = 85 + random.uniform(-10, 12)
            duration = 80 + random.uniform(-20, 30)
            
            historical.append({
                "timestamp": date.isoformat(),
                "date": date.strftime("%Y-%m-%d"),
                "total": test_count,
                "passed": int(test_count * pass_rate / 100),
                "failed": int(test_count * (100 - pass_rate) / 100),
                "coverage": round(min(100, max(0, coverage_trend)), 1),
                "duration": round(duration, 1),
                "success_rate": round(pass_rate, 1)
            })
        
        return sorted(historical, key=lambda x: x["timestamp"])
    
    def generate_demo_quality_data(self) -> Dict[str, Any]:
        """Generate code quality metrics."""
        return {
            "ruff": {
                "issues": 8,
                "errors": 2,
                "warnings": 6,
                "categories": {
                    "style": 3,
                    "complexity": 2,
                    "imports": 2,
                    "security": 1
                }
            },
            "mypy": {
                "issues": 12,
                "errors": 4,
                "warnings": 8,
                "coverage": 89.2
            },
            "complexity": {
                "average": 3.4,
                "max": 12,
                "functions_over_10": 5
            },
            "maintainability": {
                "score": 7.8,
                "grade": "B+",
                "debt_ratio": 0.08
            }
        }
    
    def generate_demo_module_data(self) -> List[Dict[str, Any]]:
        """Generate detailed module analysis data."""
        modules = [
            {"name": "Core API Client", "path": "src/mcp_vultr/server.py", "coverage": 78, "complexity": 8.2, "issues": 5},
            {"name": "FastMCP Server", "path": "src/mcp_vultr/fastmcp_server.py", "coverage": 79, "complexity": 6.1, "issues": 3},
            {"name": "CLI Interface", "path": "src/mcp_vultr/cli_main.py", "coverage": 66, "complexity": 5.4, "issues": 8},
            {"name": "TUI Application", "path": "src/mcp_vultr/tui_app.py", "coverage": 65, "complexity": 9.8, "issues": 12},
            {"name": "DNS Management", "path": "src/mcp_vultr/dns.py", "coverage": 75, "complexity": 4.2, "issues": 2},
            {"name": "Cache System", "path": "src/mcp_vultr/cache.py", "coverage": 98, "complexity": 3.1, "issues": 0},
            {"name": "Retry Logic", "path": "src/mcp_vultr/retry.py", "coverage": 90, "complexity": 2.8, "issues": 1},
            {"name": "Metrics", "path": "src/mcp_vultr/metrics.py", "coverage": 88, "complexity": 4.7, "issues": 2},
            {"name": "Client Library", "path": "src/mcp_vultr/client.py", "coverage": 86, "complexity": 5.2, "issues": 3},
            {"name": "Logging", "path": "src/mcp_vultr/logging.py", "coverage": 86, "complexity": 2.1, "issues": 1}
        ]
        
        for module in modules:
            if module["coverage"] >= 90:
                module["status"] = "excellent"
            elif module["coverage"] >= 80:
                module["status"] = "good"
            elif module["coverage"] >= 70:
                module["status"] = "warning"
            else:
                module["status"] = "critical"
        
        return modules
    
    def create_demo_html_template(self, demo_data: Dict[str, Any]) -> str:
        """Create enhanced HTML template with demo data."""
        embedded_data = json.dumps(demo_data, indent=2)
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="MCP-Vultr Testing Dashboard Demo">
    <title>MCP-Vultr Testing Dashboard - Demo</title>
    
    <style>
        {self.get_dashboard_css()}
        {self.get_demo_enhancements_css()}
    </style>
</head>
<body class="theme-gruvbox-dark">
    <div class="dashboard-container">
        {self.get_demo_header()}
        {self.get_dashboard_navigation()}
        {self.get_demo_content()}
        {self.get_dashboard_footer()}
    </div>
    
    <!-- Embedded Demo Data -->
    <script type="application/json" id="dashboard-data">
    {embedded_data}
    </script>
    
    <script>
        {self.get_dashboard_javascript()}
        {self.get_demo_enhancements_javascript()}
    </script>
</body>
</html>'''
    
    def get_demo_enhancements_css(self) -> str:
        """Additional CSS for demo features."""
        return '''
        /* Demo-specific enhancements */
        .demo-badge {
            position: fixed;
            top: 1rem;
            right: 1rem;
            background: linear-gradient(135deg, var(--gruvbox-purple), var(--gruvbox-blue));
            color: var(--gruvbox-dark0);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            z-index: 1000;
            box-shadow: 0 4px 15px rgba(211, 134, 155, 0.3);
            animation: float 3s ease-in-out infinite;
        }
        
        .demo-features {
            background: linear-gradient(135deg, var(--gruvbox-dark1), var(--gruvbox-dark2));
            border: 1px solid var(--gruvbox-purple);
            border-radius: var(--border-radius);
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .feature-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .feature-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--gruvbox-light0);
            font-size: 0.875rem;
        }
        
        .feature-check {
            color: var(--gruvbox-green);
            font-weight: bold;
        }
        
        .enhanced-metric {
            position: relative;
            overflow: hidden;
        }
        
        .enhanced-metric::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(131, 165, 152, 0.1),
                transparent
            );
            animation: enhance-sweep 3s infinite;
        }
        
        @keyframes enhance-sweep {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .demo-chart {
            background: var(--gruvbox-dark2);
            border-radius: var(--border-radius);
            padding: 1rem;
            height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        
        .demo-chart::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                linear-gradient(45deg, transparent 40%, rgba(131, 165, 152, 0.1) 50%, transparent 60%),
                linear-gradient(-45deg, transparent 40%, rgba(211, 134, 155, 0.1) 50%, transparent 60%);
            animation: chart-pattern 4s infinite;
        }
        
        @keyframes chart-pattern {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.6; }
        }
        
        .interactive-demo {
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .interactive-demo:hover {
            transform: scale(1.02);
            box-shadow: 0 8px 25px rgba(131, 165, 152, 0.2);
        }
        '''
    
    def get_demo_header(self) -> str:
        """Enhanced header for demo."""
        return '''
        <div class="demo-badge">
            🎨 DEMO
        </div>
        
        <header class="dashboard-header">
            <div class="dashboard-title">
                <h1>MCP-Vultr Testing Dashboard</h1>
                <span class="project-badge">Demo Mode</span>
            </div>
            <div class="header-stats">
                <div class="header-stat enhanced-metric">
                    <span class="header-stat-value" id="total-tests">187</span>
                    <span class="header-stat-label">Total Tests</span>
                </div>
                <div class="header-stat enhanced-metric">
                    <span class="header-stat-value" id="success-rate">88.2%</span>
                    <span class="header-stat-label">Success Rate</span>
                </div>
                <div class="header-stat enhanced-metric">
                    <span class="header-stat-value" id="coverage-percent">78.3%</span>
                    <span class="header-stat-label">Coverage</span>
                </div>
                <div class="header-stat enhanced-metric">
                    <span class="header-stat-value" id="duration">89.4s</span>
                    <span class="header-stat-label">Duration</span>
                </div>
            </div>
        </header>
        '''
    
    def get_demo_content(self) -> str:
        """Enhanced content with demo features."""
        return '''
        <main class="dashboard-content">
            <!-- Demo Features Overview -->
            <div class="demo-features">
                <h3 style="color: var(--gruvbox-purple); margin-bottom: 0.5rem;">🎨 Dashboard Features Showcase</h3>
                <div class="feature-list">
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Gruvbox Terminal Theme</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Real-time Monitoring</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Interactive Components</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Historical Trends</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Mobile Responsive</span>
                    </div>
                    <div class="feature-item">
                        <span class="feature-check">✓</span>
                        <span>Zero Dependencies</span>
                    </div>
                </div>
            </div>
            
            <!-- Overview Tab -->
            <div class="tab-content active" id="overview">
                <div class="grid-4">
                    <div class="card metric-card interactive-demo">
                        <span class="metric-value" id="overview-total">187</span>
                        <span class="metric-label">Total Tests</span>
                        <span class="metric-change positive">+25 from last run</span>
                    </div>
                    <div class="card metric-card interactive-demo">
                        <span class="metric-value" id="overview-passed">165</span>
                        <span class="metric-label">Passed</span>
                        <span class="metric-change positive">+18 from last run</span>
                    </div>
                    <div class="card metric-card interactive-demo">
                        <span class="metric-value" id="overview-failed">12</span>
                        <span class="metric-label">Failed</span>
                        <span class="metric-change negative">+3 from last run</span>
                    </div>
                    <div class="card metric-card interactive-demo">
                        <span class="metric-value" id="overview-coverage">78.3%</span>
                        <span class="metric-label">Coverage</span>
                        <span class="metric-change positive">+3.1% from last run</span>
                    </div>
                </div>
                
                <div class="grid-2" style="margin-top: 2rem;">
                    <div class="card interactive-demo">
                        <div class="card-header">
                            <h2 class="card-title">Test Categories Distribution</h2>
                            <span class="card-badge">4 categories</span>
                        </div>
                        <div class="demo-chart">
                            <div style="text-align: center; color: var(--gruvbox-light4);">
                                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                                <div>Interactive Chart Placeholder</div>
                                <div style="font-size: 0.75rem; margin-top: 0.5rem;">Unit: 95 | Integration: 52 | MCP: 28 | TUI: 12</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card interactive-demo">
                        <div class="card-header">
                            <h2 class="card-title">Success Rate Trend</h2>
                            <span class="card-badge">30 days</span>
                        </div>
                        <div class="demo-chart">
                            <div style="text-align: center; color: var(--gruvbox-light4);">
                                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📈</div>
                                <div>Trending Upward</div>
                                <div style="font-size: 0.75rem; margin-top: 0.5rem;">88.2% success rate (+5.4% this month)</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card interactive-demo" style="margin-top: 2rem;">
                    <div class="card-header">
                        <h2 class="card-title">Recent Test Failures</h2>
                        <span class="card-badge">12 failures</span>
                    </div>
                    <table class="data-table table-modern">
                        <thead>
                            <tr>
                                <th>Test Name</th>
                                <th>File</th>
                                <th>Error Type</th>
                                <th>Duration</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="recent-failures">
                            <tr class="row-critical">
                                <td>test_vultr_auth_timeout</td>
                                <td>test_client.py:145</td>
                                <td>TimeoutError</td>
                                <td>30.1s</td>
                                <td><span class="status-indicator critical"></span>Failed</td>
                            </tr>
                            <tr class="row-critical">
                                <td>test_dns_record_validation</td>
                                <td>test_server.py:89</td>
                                <td>ValidationError</td>
                                <td>2.3s</td>
                                <td><span class="status-indicator critical"></span>Failed</td>
                            </tr>
                            <tr class="row-warning">
                                <td>test_mcp_server_connection</td>
                                <td>test_mcp_server.py:203</td>
                                <td>ConnectionError</td>
                                <td>15.7s</td>
                                <td><span class="status-indicator warning"></span>Flaky</td>
                            </tr>
                            <tr class="row-critical">
                                <td>test_tui_navigation_keys</td>
                                <td>test_tui_app.py:67</td>
                                <td>KeyError</td>
                                <td>1.2s</td>
                                <td><span class="status-indicator critical"></span>Failed</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Additional tabs would be populated here -->
            {self.get_dashboard_content()}
        </main>
        '''
    
    def get_demo_enhancements_javascript(self) -> str:
        """Additional JavaScript for demo features."""
        return '''
        // Demo-specific enhancements
        function initializeDemoFeatures() {
            addDemoInteractivity();
            startDemoAnimations();
            populateDemoData();
        }
        
        function addDemoInteractivity() {
            // Add click handlers for demo elements
            document.querySelectorAll('.interactive-demo').forEach(element => {
                element.addEventListener('click', function() {
                    // Add ripple effect
                    const ripple = document.createElement('div');
                    ripple.style.cssText = `
                        position: absolute;
                        background: rgba(131, 165, 152, 0.3);
                        transform: scale(0);
                        animation: ripple 0.6s linear;
                        border-radius: 50%;
                        width: 100px;
                        height: 100px;
                        left: 50%;
                        top: 50%;
                        margin-left: -50px;
                        margin-top: -50px;
                        pointer-events: none;
                    `;
                    
                    this.style.position = 'relative';
                    this.style.overflow = 'hidden';
                    this.appendChild(ripple);
                    
                    setTimeout(() => ripple.remove(), 600);
                    
                    // Show demo info
                    showDemoNotification('This is a demo feature! In a real dashboard, this would show detailed information.', 'info');
                });
            });
        }
        
        function startDemoAnimations() {
            // Stagger card animations
            document.querySelectorAll('.card').forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.classList.add('animate-slide-in');
            });
        }
        
        function populateDemoData() {
            // Populate demo-specific data
            if (dashboardData && dashboardData.coverage) {
                const coverage = dashboardData.coverage;
                updateElement('coverage-percent', `${coverage.overall_percentage}%`);
                
                // Populate coverage heatmap with demo data
                populateDemoCoverageHeatmap();
            }
        }
        
        function populateDemoCoverageHeatmap() {
            const container = document.getElementById('coverage-heatmap');
            if (!container || !dashboardData.coverage) return;
            
            const modules = dashboardData.coverage.modules;
            
            container.innerHTML = modules.map((module, index) => `
                <div class="coverage-module interactive-demo stagger-${Math.min(index + 1, 5)}" 
                     data-tooltip="Click for detailed coverage report">
                    <div class="module-name">${module.name}</div>
                    <div class="module-coverage" style="color: var(--status-${module.status})">${module.coverage}%</div>
                    <div class="module-statements">${module.statements} statements, ${module.missing} missing</div>
                    <div class="progress-bar" style="margin-top: 0.5rem;">
                        <div class="progress-fill ${module.status}" style="width: ${module.coverage}%"></div>
                    </div>
                    <div class="status-badge ${module.status}" style="margin-top: 0.5rem; font-size: 0.6rem;">
                        ${module.status.toUpperCase()}
                    </div>
                </div>
            `).join('');
        }
        
        function showDemoNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 5rem;
                right: 1rem;
                z-index: 1002;
                background: var(--gruvbox-${type === 'success' ? 'green' : type === 'warning' ? 'yellow' : 'blue'});
                color: var(--gruvbox-dark0);
                padding: 1rem 1.5rem;
                border-radius: var(--border-radius);
                box-shadow: var(--shadow);
                transform: translateX(100%);
                transition: transform 0.3s ease-out;
                max-width: 300px;
                font-size: 0.875rem;
                line-height: 1.4;
            `;
            notification.textContent = message;
            
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.transform = 'translateX(0)';
            }, 100);
            
            // Remove after 5 seconds
            setTimeout(() => {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 5000);
        }
        
        // Add ripple animation CSS
        const demoStyles = document.createElement('style');
        demoStyles.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(demoStyles);
        
        // Initialize demo features when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {
            initializeDemoFeatures();
            
            // Show welcome message
            setTimeout(() => {
                showDemoNotification('Welcome to the MCP-Vultr Testing Dashboard Demo! Click on cards to see interactive features.', 'success');
            }, 1000);
        });
        '''


def main():
    """Generate and optionally open the demo dashboard."""
    print("🎨 Creating MCP-Vultr Testing Dashboard Demo...")
    
    demo_generator = DemoDashboardGenerator()
    dashboard_path = demo_generator.generate_demo_dashboard()
    
    # Ask if user wants to open in browser
    try:
        response = input("\n🌐 Open dashboard in browser? (y/n): ").lower().strip()
        if response in ['y', 'yes', '']:
            webbrowser.open(f"file://{Path(dashboard_path).absolute()}")
            print("✅ Dashboard opened in browser")
    except KeyboardInterrupt:
        print("\n👋 Demo generation complete")
    
    print(f"\n📂 Dashboard location: {dashboard_path}")
    print("🎯 Features demonstrated:")
    print("   • Beautiful Gruvbox terminal theme")
    print("   • Interactive components with animations") 
    print("   • Responsive design (mobile-friendly)")
    print("   • Zero external dependencies")
    print("   • Real coverage and test data visualization")
    print("   • Enterprise-grade styling")


if __name__ == "__main__":
    main()