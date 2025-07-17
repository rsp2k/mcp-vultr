#!/usr/bin/env python3
"""
Example usage of the Vultr DNS MCP package.

This script demonstrates various ways to use the package:
1. As an MCP server
2. As a Python client library
3. DNS record validation
4. Configuration analysis
"""

import asyncio
import os
from mcp_vultr import VultrDNSClient, VultrDNSServer, create_mcp_server


async def client_example():
    """Demonstrate using the VultrDNSClient."""
    print("🔧 VultrDNSClient Example")
    print("=" * 40)
    
    # Get API key from environment
    api_key = os.getenv("VULTR_API_KEY")
    if not api_key:
        print("❌ VULTR_API_KEY environment variable not set")
        print("Set your API key: export VULTR_API_KEY='your-key-here'")
        return
    
    try:
        client = VultrDNSClient(api_key)
        
        # List domains
        print("📋 Listing domains:")
        domains = await client.domains()
        for domain in domains[:3]:  # Show first 3
            print(f"  • {domain.get('domain', 'Unknown')}")
        
        if domains:
            domain_name = domains[0].get('domain')
            
            # Get domain summary
            print(f"\n📊 Domain summary for {domain_name}:")
            summary = await client.get_domain_summary(domain_name)
            if "error" not in summary:
                print(f"  Total records: {summary['total_records']}")
                print(f"  Record types: {summary['record_types']}")
                config = summary['configuration']
                print(f"  Has root record: {'✅' if config['has_root_record'] else '❌'}")
                print(f"  Has www: {'✅' if config['has_www_subdomain'] else '❌'}")
                print(f"  Has email: {'✅' if config['has_email_setup'] else '❌'}")
        
        print("\n✅ Client example completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def server_example():
    """Demonstrate creating an MCP server."""
    print("\n🚀 MCP Server Example")
    print("=" * 40)
    
    api_key = os.getenv("VULTR_API_KEY")
    if not api_key:
        print("❌ VULTR_API_KEY environment variable not set")
        return
    
    try:
        # Create MCP server
        mcp_server = create_mcp_server(api_key)
        print(f"✅ Created MCP server: {mcp_server.name}")
        print(f"📝 Description: {mcp_server.description}")
        print("🔄 To run: call mcp_server.run()")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def validation_example():
    """Demonstrate DNS record validation."""
    print("\n🔍 DNS Record Validation Example")
    print("=" * 40)
    
    # Import the validation from the server module
    from mcp_vultr.server import create_mcp_server
    
    # Create a test server instance for validation (won't make API calls)
    try:
        server = create_mcp_server("test-key-for-validation")
        
        # Test validation examples
        test_cases = [
            {
                "record_type": "A",
                "name": "www",
                "data": "192.168.1.100",
                "description": "Valid A record"
            },
            {
                "record_type": "A",
                "name": "test",
                "data": "invalid-ip",
                "description": "Invalid A record (bad IP)"
            },
            {
                "record_type": "CNAME",
                "name": "@",
                "data": "example.com",
                "description": "Invalid CNAME (root domain)"
            },
            {
                "record_type": "MX",
                "name": "@",
                "data": "mail.example.com",
                "description": "Invalid MX (missing priority)"
            }
        ]
        
        for i, test in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test['description']}")
            print(f"  Type: {test['record_type']}, Name: {test['name']}, Data: {test['data']}")
            
            # Simulate validation (this would normally be done through the MCP tool)
            # For demo purposes, we'll do basic validation here
            if test['record_type'] == 'A':
                import re
                pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
                valid = re.match(pattern, test['data']) is not None
                print(f"  Result: {'✅ Valid' if valid else '❌ Invalid IP address'}")
            elif test['record_type'] == 'CNAME' and test['name'] == '@':
                print("  Result: ❌ CNAME cannot be used for root domain")
            elif test['record_type'] == 'MX':
                print("  Result: ❌ MX records require a priority value")
            else:
                print("  Result: ✅ Valid")
        
    except ValueError:
        # Expected error for invalid API key, but we can still show the structure
        print("✅ Validation examples shown (API key not needed for validation logic)")


async def main():
    """Run all examples."""
    print("🧪 Vultr DNS MCP Package Examples")
    print("=" * 50)
    
    # Show client usage
    await client_example()
    
    # Show server creation
    server_example()
    
    # Show validation
    await validation_example()
    
    print("\n" + "=" * 50)
    print("📚 More Information:")
    print("  • Documentation: https://mcp-vultr.readthedocs.io/")
    print("  • PyPI: https://pypi.org/project/mcp-vultr/")
    print("  • CLI Help: mcp-vultr --help")
    print("  • Start MCP Server: mcp-vultr server")


if __name__ == "__main__":
    asyncio.run(main())
