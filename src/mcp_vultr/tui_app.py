"""
Awesome Textual TUI Application for Vultr Management.

This module provides a beautiful, interactive terminal interface
showcasing the full power of the Vultr API and MCP integration.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from rich.align import Align
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
    Footer,
    Header,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from ._version import __version__


class ChatPromptsLoader:
    """Load and manage chat prompts from JSON file."""

    def __init__(self, prompts_file: str = "chat_prompts.json"):
        self.prompts_file = Path(prompts_file)
        self.prompts_data = self._load_prompts()

    def _load_prompts(self) -> dict:
        """Load prompts from JSON file."""
        try:
            if self.prompts_file.exists():
                with open(self.prompts_file, encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

        # Fallback default prompts
        return {
            "categories": {
                "vultr_cloud": {
                    "title": "Vultr Cloud Management",
                    "prompts": [
                        "List all my Vultr instances across regions and show their current status, IP addresses, and monthly costs.",
                        "Create a new compute instance in the New York datacenter with 2GB RAM and deploy Ubuntu 22.04.",
                        "Show me the DNS records for my domain and add a new CNAME record.",
                    ],
                }
            }
        }

    def get_random_prompt(self) -> tuple[str, str]:
        """Get a random prompt with its category title."""
        categories = self.prompts_data.get("categories", {})
        if not categories:
            return "Demo", "Welcome to the Vultr Management TUI!"

        category_key = random.choice(list(categories.keys()))
        category = categories[category_key]
        prompt = random.choice(category.get("prompts", ["Welcome!"]))

        return category.get("title", category_key), prompt

    def get_all_prompts(self) -> list[tuple[str, str]]:
        """Get all prompts with their category titles."""
        all_prompts = []
        categories = self.prompts_data.get("categories", {})

        for category in categories.values():
            title = category.get("title", "Unknown")
            for prompt in category.get("prompts", []):
                all_prompts.append((title, prompt))

        return all_prompts


class StarWarsScroll(Static):
    """A Star Wars-style scrolling text widget for chat prompts."""

    scroll_position: reactive[int] = reactive(0)

    def __init__(self, prompts_loader: ChatPromptsLoader, **kwargs):
        super().__init__(**kwargs)
        self.prompts_loader = prompts_loader
        self.current_prompt = ""
        self.current_category = ""
        self.scroll_timer: Timer | None = None
        self.lines: list[str] = []
        self.max_width = 60

    def on_mount(self) -> None:
        """Start the scrolling animation."""
        self._load_new_prompt()
        self.scroll_timer = self.set_interval(0.1, self._update_scroll)

    def _load_new_prompt(self) -> None:
        """Load a new random prompt."""
        self.current_category, self.current_prompt = (
            self.prompts_loader.get_random_prompt()
        )
        self._prepare_text()
        self.scroll_position = len(self.lines) + 5  # Start below visible area

    def _prepare_text(self) -> None:
        """Prepare the text for scrolling display."""
        # Create title
        title_lines = [
            "",
            f"💫 {self.current_category.upper()} 💫",
            "=" * len(self.current_category),
            "",
        ]

        # Wrap the prompt text
        words = self.current_prompt.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= self.max_width:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        # Center the text
        centered_lines = []
        for line in title_lines + lines:
            if line.strip():
                padding = max(0, (self.max_width - len(line)) // 2)
                centered_lines.append(" " * padding + line)
            else:
                centered_lines.append("")

        self.lines = centered_lines + ["", "", "", ""]  # Add trailing space

    def _update_scroll(self) -> None:
        """Update scroll position."""
        self.scroll_position -= 1

        # If fully scrolled off screen, load new prompt
        if self.scroll_position < -len(self.lines) - 5:
            self._load_new_prompt()

        self.refresh()

    def render(self) -> Panel:
        """Render the scrolling text."""
        content_lines = []
        visible_height = 12  # Height of the visible area

        # Calculate which lines should be visible
        for i in range(visible_height):
            line_index = self.scroll_position - i
            if 0 <= line_index < len(self.lines):
                line = self.lines[line_index]
                # Add perspective effect (fade at top and bottom)
                if i < 2 or i > visible_height - 3:
                    line = f"[dim]{line}[/dim]"
                content_lines.append(line)
            else:
                content_lines.append("")

        # Reverse to scroll from bottom to top
        content_lines.reverse()

        content = "\n".join(content_lines)

        return Panel(
            Align.center(content, vertical="middle"),
            title="[bold cyan]✨ Chat Prompt Showcase ✨[/bold cyan]",
            subtitle="[dim]Press any key for new prompt[/dim]",
            border_style="bright_blue",
            padding=(1, 2),
        )

    def on_key(self, event) -> None:
        """Load new prompt on any keypress."""
        self._load_new_prompt()


class WelcomeScreen(Static):
    """Welcome screen with Vultr branding and animated chat prompts."""

    def compose(self) -> ComposeResult:
        # Load chat prompts
        prompts_loader = ChatPromptsLoader()

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
        """

        with Horizontal():
            with Vertical():
                yield Markdown(welcome_md)
            with Vertical():
                yield StarWarsScroll(prompts_loader, id="chat_scroll")

        # Footer with credits
        footer_md = """
---
*Powered by the Vultr API • Built with Textual • Integrated with MCP*
        """
        yield Markdown(footer_md)


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


class ChatPromptsShowcaseScreen(ScrollableContainer):
    """Interactive showcase of chat prompts with full screen Star Wars scroll."""

    def compose(self) -> ComposeResult:
        # Load chat prompts
        prompts_loader = ChatPromptsLoader()

        # Full screen scroll
        yield StarWarsScroll(prompts_loader, id="fullscreen_scroll")

        # Instructions
        instructions = """
### 🎬 Chat Prompts Cinema Mode

This screen showcases example chat prompts that demonstrate the power of AI-assisted workflows.
The prompts continuously scroll in a Star Wars-style animation.

**Features:**
- **Dynamic Content**: Prompts loaded from JSON configuration
- **Multiple Categories**: Blender automation, cloud management, MCP integration, and more
- **Interactive**: Press any key to load a new random prompt
- **Cinematic Experience**: Smooth scrolling animation with perspective effects

**Categories Available:**
- 🎨 bpy Automation & Production Pipeline
- 🔧 Addon Interaction
- 📐 bmesh & Procedural Geometry
- 🎮 Game Development Pipeline
- 🏢 Architectural Visualization & BIM
- 🔬 Scientific Visualization & Data
- 🤖 AI-Assisted Creativity
- ☁️ Vultr Cloud Management
- 🔌 MCP Server Integration

Press any key to cycle through prompts, or switch to other tabs to explore the TUI!
        """

        yield Markdown(instructions)


class APIShowcaseScreen(ScrollableContainer):
    """Interactive showcase of Vultr API capabilities."""

    def compose(self) -> ComposeResult:
        yield Static("🌟 Vultr API Showcase", classes="header")

        # Service categories with tool counts
        categories = [
            (
                "💻 Compute Services",
                [
                    "Instances (15 tools)",
                    "Bare Metal (12 tools)",
                    "Kubernetes (18 tools)",
                ],
            ),
            (
                "🌐 Networking",
                [
                    "DNS Management (19 tools)",
                    "Load Balancers (14 tools)",
                    "VPCs (16 tools)",
                    "Reserved IPs (8 tools)",
                ],
            ),
            (
                "📦 Storage",
                [
                    "Block Storage (11 tools)",
                    "Object Storage (15 tools)",
                    "Backups (9 tools)",
                    "Snapshots (7 tools)",
                ],
            ),
            (
                "🔐 Security",
                [
                    "Firewalls (12 tools)",
                    "SSH Keys (6 tools)",
                    "Users Management (9 tools)",
                ],
            ),
            (
                "📊 Management",
                [
                    "Billing (8 tools)",
                    "Metrics (6 tools)",
                    "Regions (5 tools)",
                    "Plans (7 tools)",
                ],
            ),
            (
                "🚀 Advanced",
                [
                    "CDN (13 tools)",
                    "Container Registry (11 tools)",
                    "Serverless Inference (8 tools)",
                    "Storage Gateways (9 tools)",
                ],
            ),
        ]

        tree = Tree("🌟 Vultr API Services (335+ Tools Total)", id="api_tree")

        for category, tools in categories:
            category_node = tree.root.add(category, expand=True)
            for tool in tools:
                category_node.add_leaf(f"  {tool}")

        yield tree

        yield Static(
            "💡 All these tools are available through the MCP server!", classes="info"
        )


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

            with TabPane("🎬 Chat Prompts", id="prompts"):
                yield ChatPromptsShowcaseScreen()

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
