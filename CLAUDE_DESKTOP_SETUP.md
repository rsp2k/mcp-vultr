# Testing Vultr DNS MCP in Claude Desktop

This guide shows how to set up and test the Vultr DNS MCP package locally with Claude Desktop.

## Prerequisites

1. **Claude Desktop** installed on your machine
2. **Vultr API Key** - Get from [Vultr Account > API](https://my.vultr.com/settings/#settingsapi)
3. **Python 3.10+** with the package installed

## Installation Options

### Option 1: Install from PyPI (Recommended)
```bash
pip install vultr-dns-mcp
```

### Option 2: Install from Local Development
```bash
# From this project directory
pip install -e .
```

### Option 3: Using uv (Fastest)
```bash
uv add vultr-dns-mcp
```

## Claude Desktop Configuration

### 1. Locate Claude Desktop Config

The configuration file location depends on your OS:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add MCP Server Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vultr-dns": {
      "command": "python",
      "args": ["-m", "vultr_dns_mcp.server"],
      "env": {
        "VULTR_API_KEY": "YOUR_VULTR_API_KEY_HERE"
      }
    }
  }
}
```

### 3. Alternative: Using uv (if you have it)

```json
{
  "mcpServers": {
    "vultr-dns": {
      "command": "uv",
      "args": ["run", "python", "-m", "vultr_dns_mcp.server"],
      "env": {
        "VULTR_API_KEY": "YOUR_VULTR_API_KEY_HERE"
      }
    }
  }
}
```

### 4. Using Absolute Path (Most Reliable)

If you have issues, use the absolute path to your Python installation:

```json
{
  "mcpServers": {
    "vultr-dns": {
      "command": "/usr/bin/python3",
      "args": ["-m", "vultr_dns_mcp.server"],
      "env": {
        "VULTR_API_KEY": "YOUR_VULTR_API_KEY_HERE"
      }
    }
  }
}
```

## Testing the Setup

### 1. Restart Claude Desktop
After saving the configuration file, completely restart Claude Desktop.

### 2. Test MCP Connection
In Claude Desktop, you should see:
- An indicator that the MCP server is connected
- Access to Vultr DNS tools in the interface

### 3. Example Prompts to Try

Once connected, try these prompts in Claude Desktop:

```
"List all my DNS domains"
```

```
"Show me the DNS records for example.com"
```

```
"Create an A record for www.example.com pointing to 192.168.1.100"
```

```
"Analyze the DNS configuration for my domain and suggest improvements"
```

```
"Set up basic website DNS for newdomain.com with IP 203.0.113.10"
```

## Available MCP Tools

The server provides these tools that Claude Desktop can use:

1. **list_dns_domains** - List all your DNS domains
2. **get_dns_domain** - Get details for a specific domain
3. **create_dns_domain** - Create a new DNS domain
4. **delete_dns_domain** - Delete a domain and all its records
5. **list_dns_records** - List DNS records for a domain
6. **get_dns_record** - Get details for a specific record
7. **create_dns_record** - Create a new DNS record
8. **update_dns_record** - Update an existing record
9. **delete_dns_record** - Delete a DNS record
10. **validate_dns_record** - Validate a record before creation
11. **analyze_dns_records** - Analyze domain DNS configuration
12. **setup_website_dns** - Quick setup for website DNS

## Troubleshooting

### MCP Server Won't Start

1. **Check Python installation**:
   ```bash
   python -c "import vultr_dns_mcp; print('✅ Package installed')"
   ```

2. **Test server manually**:
   ```bash
   export VULTR_API_KEY="your-key"
   python -m vultr_dns_mcp.server
   ```

3. **Check API key**:
   ```bash
   export VULTR_API_KEY="your-key"
   python -c "
   from vultr_dns_mcp.client import VultrDNSClient
   import asyncio
   async def test():
       client = VultrDNSClient()
       domains = await client.domains()
       print(f'✅ Found {len(domains)} domains')
   asyncio.run(test())
   "
   ```

### Path Issues

If Claude Desktop can't find Python:

1. **Find your Python path**:
   ```bash
   which python3
   # or
   which python
   ```

2. **Update config with full path**:
   ```json
   {
     "mcpServers": {
       "vultr-dns": {
         "command": "/full/path/to/python3",
         "args": ["-m", "vultr_dns_mcp.server"],
         "env": {
           "VULTR_API_KEY": "YOUR_KEY"
         }
       }
     }
   }
   ```

### Virtual Environment Issues

If using a virtual environment:

1. **Activate and find Python**:
   ```bash
   source your-venv/bin/activate  # or your-venv\Scripts\activate on Windows
   which python
   ```

2. **Use that path in config**:
   ```json
   {
     "mcpServers": {
       "vultr-dns": {
         "command": "/path/to/your-venv/bin/python",
         "args": ["-m", "vultr_dns_mcp.server"],
         "env": {
           "VULTR_API_KEY": "YOUR_KEY"
         }
       }
     }
   }
   ```

## Security Notes

- Keep your Vultr API key secure
- Consider using environment variables instead of hardcoding in config
- The API key has access to modify your DNS records

## Example Natural Language Interactions

Once set up, you can use natural language with Claude Desktop:

- "What domains do I have in Vultr?"
- "Add a CNAME record for blog.example.com pointing to example.com"
- "Delete the old MX record for example.com"
- "Set up email DNS for my domain with mail.example.com as the mail server"
- "Check if my domain has proper SPF and DMARC records"
- "Create an IPv6 AAAA record for www pointing to 2001:db8::1"

Claude Desktop will use the MCP tools to perform these operations on your behalf!

## Next Steps

- Try the natural language prompts above
- Explore the comprehensive DNS management capabilities
- Use the analysis features to improve your DNS setup
- Set up automation for common DNS tasks

Happy DNS managing! 🎉