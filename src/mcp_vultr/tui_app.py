"""
Awesome Textual TUI Application for Vultr Management.

This module provides a beautiful, interactive terminal interface
showcasing the full power of the Vultr API and MCP integration.
"""

from __future__ import annotations

import asyncio
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button,
    Header,
    Footer,
    Static,
    TabbedContent,
    TabPane,
    Tree,
    ProgressBar,
    DataTable,
    Markdown,
    Label,
    Input,
    Select,
    TextArea,
)
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax

from ._version import __version__


class WelcomeScreen(Static):
    """Welcome screen with Vultr branding and overview."""

    def compose(self) -> ComposeResult:
        welcome_md = f"""
# 🌟 Welcome to Vultr Management TUI v{__version__}

## Your Gateway to Cloud Excellence

This **interactive terminal interface** showcases the complete power of the Vultr API with **335+ management tools** integrated through the Model Context Protocol (MCP).

### 🚀 What You Can Do:

- **🖥️ Compute Management**: Deploy instances, bare metal servers, and Kubernetes clusters
- **🌐 DNS Management**: Complete domain and record management
- **📦 Storage Solutions**: Block storage, object storage, and CDN management  
- **🔐 Security & Networking**: VPCs, firewalls, and load balancers
- **🤖 AI Integration**: MCP server setup for Claude Desktop, VS Code, and more
- **⚡ Real-time Monitoring**: Live metrics and performance insights

### 💡 Getting Started:

Use the **tabs above** to explore different areas, or press **Ctrl+H** for help!

---
*Powered by the Vultr API • Built with Textual • Integrated with MCP*
        """
        
        yield Markdown(welcome_md)


class MCPSetupScreen(Static):
    """MCP server setup guide for different chat clients."""

    def compose(self) -> ComposeResult:
        setup_md = """
# 🤖 MCP Server Setup Guide

## Claude Desktop Integration

### Step 1: Install Package
```bash
pip install mcp-vultr
# or
uvx mcp-vultr  # for isolated execution
```

### Step 2: Configure Claude Desktop
Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vultr": {
      "command": "mcp-vultr",
      "env": {
        "VULTR_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop
The Vultr MCP server will be available with **335+ tools**!

## VS Code Integration

### Using Claude Code Extension:
```bash
claude mcp add vultr "mcp-vultr"
```

## Other Clients

### Universal MCP Connection:
- **Server Command**: `mcp-vultr`
- **Environment**: `VULTR_API_KEY=your-key`
- **Protocol**: Model Context Protocol v1.0

## API Key Setup

1. Visit [Vultr API Dashboard](https://my.vultr.com/settings/#settingsapi)
2. Generate a new API key
3. Set environment variable: `export VULTR_API_KEY="your-key"`

---
*Need help? Check the documentation or contact support!*
        """
        
        yield Markdown(setup_md)


class APIShowcaseScreen(ScrollableContainer):
    """Interactive showcase of Vultr API capabilities."""

    def compose(self) -> ComposeResult:
        yield Static("🌟 Vultr API Showcase", classes="header")
        
        # Service categories with tool counts
        categories = [
            ("💻 Compute Services", [
                "Instances (15 tools)", 
                "Bare Metal (12 tools)",
                "Kubernetes (18 tools)"
            ]),
            ("🌐 Networking", [
                "DNS Management (19 tools)",
                "Load Balancers (14 tools)", 
                "VPCs (16 tools)",
                "Reserved IPs (8 tools)"
            ]),
            ("📦 Storage", [
                "Block Storage (11 tools)",
                "Object Storage (15 tools)",
                "Backups (9 tools)",
                "Snapshots (7 tools)"
            ]),
            ("🔐 Security", [
                "Firewalls (12 tools)",
                "SSH Keys (6 tools)",
                "Users Management (9 tools)"
            ]),
            ("📊 Management", [
                "Billing (8 tools)",
                "Metrics (6 tools)",
                "Regions (5 tools)",
                "Plans (7 tools)"
            ]),
            ("🚀 Advanced", [
                "CDN (13 tools)",
                "Container Registry (11 tools)",
                "Serverless Inference (8 tools)",
                "Storage Gateways (9 tools)"
            ])
        ]
        
        tree = Tree("🌟 Vultr API Services (335+ Tools Total)", id="api_tree")
        
        for category, tools in categories:
            category_node = tree.root.add(category, expand=True)
            for tool in tools:
                category_node.add_leaf(f"  {tool}")
        
        yield tree
        
        yield Static("💡 All these tools are available through the MCP server!", 
                    classes="info")


class HelpScreen(Static):
    """Help and CLI usage examples."""

    def compose(self) -> ComposeResult:
        help_md = """
# 📚 Help & CLI Usage

## Command Line Interface

### Basic Usage:
```bash
vultr-cli --help                 # Show main help
vultr-cli domains list           # List DNS domains
vultr-cli records create         # Create DNS record
vultr-cli bare-metal list        # List bare metal servers
```

### MCP Server:
```bash
mcp-vultr                        # Start MCP server
```

### Service Categories:
- `bare-metal` - Bare metal server management
- `billing` - Account and billing information  
- `block-storage` - Block storage volumes
- `cdn` - CDN zone management
- `container-registry` - Container registries
- `databases` - Managed databases
- `domains` - DNS domain management
- `iso` - ISO image management
- `kubernetes` - Kubernetes clusters
- `load-balancer` - Load balancer management
- `object-storage` - Object storage buckets
- `operating-systems` - Available OS images
- `plans` - Hosting plans and pricing
- `records` - DNS record management
- `startup-scripts` - Server startup scripts
- `users` - User management
- `vpcs` - VPC network management

## Keyboard Shortcuts

- **Ctrl+Q**: Quit application
- **Ctrl+H**: Show this help
- **Tab**: Navigate between tabs
- **Enter**: Execute selected action

## Environment Variables

- `VULTR_API_KEY`: Your Vultr API key (required)
- `VULTR_DEBUG`: Enable debug logging

---
*For more help, visit the documentation or GitHub repository!*
        """
        
        yield Markdown(help_md)


class VultrTUI(App):
    """The main Vultr TUI application."""
    
    CSS = """
    Screen {
        background: $background 90%;
    }
    
    .header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }
    
    .info {
        dock: bottom;
        height: 3;
        background: $secondary;
        color: $text;
        content-align: center middle;
        text-style: italic;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    Tree {
        background: $surface;
        color: $text;
        scrollbar-background: $surface;
        scrollbar-color: $primary;
    }
    
    Markdown {
        background: $surface;
        color: $text;
        margin: 1;
        padding: 1;
    }
    """
    
    TITLE = "Vultr Management TUI"
    SUB_TITLE = f"v{__version__} • 335+ API Tools • MCP Integration"
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+h", "show_help", "Help"),
        ("ctrl+s", "show_setup", "MCP Setup"),
    ]

    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()
        
        with TabbedContent(initial="welcome"):
            with TabPane("🏠 Welcome", id="welcome"):
                yield WelcomeScreen()
            
            with TabPane("🤖 MCP Setup", id="setup"):
                yield MCPSetupScreen()
            
            with TabPane("🚀 API Showcase", id="showcase"):
                yield APIShowcaseScreen()
            
            with TabPane("📚 Help", id="help"):
                yield HelpScreen()
        
        yield Footer()

    def action_show_help(self) -> None:
        """Show the help tab."""
        self.query_one(TabbedContent).active = "help"
    
    def action_show_setup(self) -> None:
        """Show the MCP setup tab."""
        self.query_one(TabbedContent).active = "setup"


def run_tui() -> None:
    """Launch the Vultr TUI application."""
    app = VultrTUI()
    app.run()


if __name__ == "__main__":
    run_tui()