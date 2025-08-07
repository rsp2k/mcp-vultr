<div align="center">

# 🌩️ Vultr MCP

**The Ultimate Model Context Protocol Server for Vultr Cloud Management**

*Transform your cloud infrastructure with natural language commands*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/mcp-vultr.svg)](https://pypi.org/project/mcp-vultr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Downloads](https://img.shields.io/pypi/dm/mcp-vultr.svg)](https://pypi.org/project/mcp-vultr/)

[🚀 Quick Start](#-quick-start) • [📖 Documentation](#-documentation) • [🛠️ Features](#-features) • [💡 Examples](#-examples) • [🤝 Contributing](#-contributing)

</div>

---

## 🎯 What is Vultr MCP?

**Vultr MCP** is the most comprehensive Model Context Protocol server for Vultr cloud services, bringing **335+ management tools** across **27 service modules** to your fingertips. Manage your entire Vultr infrastructure through natural language conversations with Claude Code, Claude Desktop, or any MCP-compatible AI assistant.

### ⚡ **Why Choose Vultr MCP?**

- 🎛️ **Complete Control**: Manage every aspect of your Vultr infrastructure
- 🧠 **AI-Native**: Built specifically for natural language cloud management  
- 🔍 **Smart Identifiers**: Use human names instead of cryptic UUIDs
- 🚀 **Production Ready**: Battle-tested with comprehensive error handling
- 🌐 **Full Coverage**: From DNS to Kubernetes, databases to CDN

---

## 🛠️ **Features**

### 🌟 **Core Capabilities**

<table>
<tr>
<td width="50%">

**🎯 Smart Management**
- 🔤 Human-readable identifiers
- 🛡️ Intelligent validation  
- 📊 Real-time analytics
- 🔄 Bulk operations

</td>
<td width="50%">

**⚡ Developer Experience**
- 🐍 Native Python API
- 🖥️ Rich CLI interface
- 📚 Comprehensive docs
- 🧪 Full test coverage

</td>
</tr>
</table>

### 🏗️ **Service Coverage (335+ Tools)**

<details>
<summary><strong>🖥️ Compute & Infrastructure (67 tools)</strong></summary>

| Service | Tools | Smart Identifiers |
|---------|-------|------------------|
| **Instances** | 14 | `label`, `hostname` |
| **Bare Metal** | 18 | `label`, `hostname` |
| **Reserved IPs** | 11 | IP address |
| **SSH Keys** | 5 | `name` |
| **Snapshots** | 6 | `description` |
| **Backups** | 2 | UUID |
| **Regions** | 5 | Region code |
| **Plans** | 10 | Plan ID |

</details>

<details>
<summary><strong>🌐 Networking & DNS (54 tools)</strong></summary>

| Service | Tools | Smart Identifiers |
|---------|-------|------------------|
| **DNS Management** | 14 | Domain name |
| **VPCs & VPC 2.0** | 15 | `description` |
| **Load Balancers** | 16 | `name`, `label` |
| **CDN & Edge** | 15 | Origin/CDN domain |
| **Firewall** | 10 | `description` |

</details>

<details>
<summary><strong>🗄️ Storage & Data (53 tools)</strong></summary>

| Service | Tools | Smart Identifiers |
|---------|-------|------------------|
| **Managed Databases** | 41 | `name`, `label` |
| **Block Storage** | 12 | `label` |
| **Object Storage** | 12 | `name`, `label` |
| **Storage Gateways** | 14 | `name`, `label` |

</details>

<details>
<summary><strong>🐳 Containers & Apps (45 tools)</strong></summary>

| Service | Tools | Smart Identifiers |
|---------|-------|------------------|
| **Kubernetes** | 24 | Cluster `name`/`label` |
| **Container Registry** | 10 | Registry `name` |
| **Serverless Inference** | 10 | Service `name`/`label` |
| **Marketplace** | 11 | App name |

</details>

<details>
<summary><strong>🔧 Management & Operations (40+ tools)</strong></summary>

| Service | Tools | Smart Identifiers |
|---------|-------|------------------|
| **Billing & Account** | 12 | Account info |
| **Users & Subaccounts** | 23 | Email, name |
| **Startup Scripts** | 10 | Script `name` |
| **ISO Images** | 7 | Filename |
| **Operating Systems** | 8 | OS name |

</details>

---

## 🚀 **Quick Start**

### 📦 **Installation**

```bash
# 🏃‍♂️ Fast installation with uv (recommended)
uv add mcp-vultr

# 📦 Traditional pip installation  
pip install mcp-vultr
```

### ⚙️ **Setup with Claude Code**

```bash
# 🔑 Set your Vultr API key
export VULTR_API_KEY="your-vultr-api-key"

# 🔌 Add to Claude Code (one command!)
claude mcp add vultr vultr-mcp-server --env VULTR_API_KEY="${VULTR_API_KEY}"
```

### 🎉 **Start Managing!**

```bash
# 🚀 Launch the MCP server
vultr-mcp-server
```

**That's it!** You now have 335+ Vultr management tools available through natural language in Claude Code.

---

## 💡 **Examples**

### 🗣️ **Natural Language Commands**

```
🧑‍💻 "Create a web server instance called 'my-website' in New Jersey"
🤖 ✅ Created instance 'my-website' (Ubuntu 22.04, 1GB RAM) in ewr region

🧑‍💻 "Add a DNS record for blog.example.com pointing to my-website"  
🤖 ✅ Added A record: blog.example.com → 192.168.1.100 (TTL: 300)

🧑‍💻 "Scale my Kubernetes cluster to 5 nodes"
🤖 ✅ Scaled cluster 'production' node pool to 5 nodes

🧑‍💻 "Show me this month's billing breakdown by service"
🤖 📊 Monthly costs: Instances $45, Kubernetes $120, Storage $23...
```

### 🐍 **Python API**

```python
import asyncio
from mcp_vultr import VultrDNSClient, VultrDNSServer

async def deploy_website():
    """🚀 Deploy a complete website infrastructure"""
    
    # High-level DNS client
    dns = VultrDNSClient("your-api-key")
    
    # Full API client with smart identifiers
    vultr = VultrDNSServer("your-api-key")
    
    # 🌐 Create domain and DNS records
    await dns.create_domain("mysite.com", "192.168.1.100") 
    await dns.add_a_record("mysite.com", "www", "192.168.1.100")
    await dns.add_mx_record("mysite.com", "@", "mail.mysite.com", 10)
    
    # 🖥️ Deploy instance with smart naming
    instance = await vultr.create_instance(
        region="ewr",
        plan="vc2-1c-1gb", 
        os_id=387,
        label="web-server",  # 🏷️ Human-readable name!
        hostname="web.mysite.com"
    )
    
    # 🔥 Configure firewall by description
    firewall = await vultr.get_firewall_group("web-servers")
    
    # 📊 Get real-time metrics
    stats = await vultr.get_instance_bandwidth("web-server")  # By name!
    
    print(f"✅ Deployed {instance['label']} with {stats['incoming']}GB traffic")

asyncio.run(deploy_website())
```

### 🖥️ **CLI Power User**

```bash
# 🏗️ Infrastructure management with smart names
mcp-vultr instances create --label "api-server" --region ewr --plan vc2-2c-4gb
mcp-vultr instances start api-server                    # Start by name!
mcp-vultr instances attach-volume api-server db-storage # Attach by names!

# 🌐 DNS management
mcp-vultr domains create api.mycompany.com 192.168.1.200
mcp-vultr records add api.mycompany.com A @ 192.168.1.200
mcp-vultr setup-website api.mycompany.com 192.168.1.200 --ssl

# 🐳 Kubernetes cluster management  
mcp-vultr k8s create production-cluster --region ewr --nodes 3
mcp-vultr k8s scale production-cluster --nodes 5       # Scale by name!
mcp-vultr k8s get-costs production-cluster             # Cost analysis!

# 💾 Database deployment
mcp-vultr databases create postgres-main --engine postgresql --region ewr
mcp-vultr databases backup postgres-main               # Backup by name!

# 📊 Monitoring & analytics
mcp-vultr billing summary --month current
mcp-vultr billing trends --months 6
mcp-vultr instances list --status running --region ewr
```

---

## 🎯 **Smart Identifier Resolution**

**Stop wrestling with UUIDs!** Vultr MCP's killer feature is **smart identifier resolution** - use human-readable names instead of cryptic UUIDs across all services.

### 🏷️ **Before vs After**

```bash
# 😤 The old way (UUIDs everywhere)
vultr instance stop cb676a46-66fd-4dfb-b839-443f2e6c0b60
vultr firewall rule add 5f2a4b6c-7b8d-4e9f-a1b2-3c4d5e6f7a8b --port 443

# 🎉 The Vultr MCP way (human names!)
mcp-vultr instances stop web-server  
mcp-vultr firewall rules add web-servers --port 443
```

### 🧠 **Smart Resolution Across All Services**

| Service | Smart Identifier | Example |
|---------|------------------|---------|
| 🖥️ **Instances** | `label`, `hostname` | `web-server`, `api.company.com` |
| 🔑 **SSH Keys** | `name` | `laptop-key`, `ci-deploy-key` |
| 🔥 **Firewall Groups** | `description` | `web-servers`, `database-tier` |
| 📸 **Snapshots** | `description` | `backup-2024-01`, `pre-upgrade` |
| 🌐 **Reserved IPs** | IP address | `192.168.1.100` |
| 🐳 **Container Registries** | `name` | `my-app-registry` |
| 💾 **Block Storage** | `label` | `database-storage` |
| 🌐 **VPCs** | `description` | `production-network` |
| 📜 **Startup Scripts** | `name` | `docker-setup` |
| 🖥️ **Bare Metal** | `label`, `hostname` | `db-server-01` |
| 🌐 **CDN Zones** | Origin/CDN domain | `cdn.mysite.com` |
| ☸️ **Kubernetes** | `name`, `label` | `prod-cluster` |
| ⚖️ **Load Balancers** | `name`, `label` | `api-lb` |
| 🗄️ **Databases** | `name`, `label` | `postgres-main` |
| 💎 **Object Storage** | `name`, `label` | `media-bucket` |
| 🚀 **Inference Services** | `name`, `label` | `ml-api` |
| 🚪 **Storage Gateways** | `name`, `label` | `file-gateway` |
| 👥 **Subaccounts** | `name`, `email` | `dev-team` |
| 👤 **Users** | Email address | `admin@company.com` |

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        🤖 AI Assistant                          │
│                     (Claude Code/Desktop)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Natural Language Commands
┌──────────────────────────▼──────────────────────────────────────┐
│                   📡 Vultr MCP Server                           │
│                      (335+ Tools)                               │
├─────────────────────────────────────────────────────────────────┤
│  🌐 DNS  🖥️ Compute  🐳 K8s  🗄️ DB  🔥 Security  💾 Storage    │
│  📊 Analytics  🌍 CDN  ⚖️ LB  🚀 Serverless  👥 Users          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Smart API Calls
┌──────────────────────────▼──────────────────────────────────────┐
│                      ☁️ Vultr Cloud API                         │
│              (Complete Infrastructure Management)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📖 **Documentation**

### 🚀 **Getting Started**

- [⚡ Quick Start Guide](#-quick-start)
- [🔧 Installation & Setup](#-installation)  
- [🎯 First Steps with Claude Code](#-setup-with-claude-code)

### 📚 **API Reference**

- [🐍 Python API Documentation](https://git.supported.systems/MCP/mcp-vultr/blob/main/docs/api.md)
- [🖥️ CLI Command Reference](https://git.supported.systems/MCP/mcp-vultr/blob/main/docs/cli.md)
- [🤖 MCP Tools Reference](https://git.supported.systems/MCP/mcp-vultr/blob/main/docs/mcp-tools.md)

### 🎓 **Tutorials & Examples**

- [🏗️ Infrastructure as Code with Natural Language](https://git.supported.systems/MCP/mcp-vultr/blob/main/examples/iac.md)
- [🌐 Complete Website Deployment](https://git.supported.systems/MCP/mcp-vultr/blob/main/examples/website.md)
- [☸️ Kubernetes Cluster Management](https://git.supported.systems/MCP/mcp-vultr/blob/main/examples/kubernetes.md)

---

## 🛠️ **Development**

### 🏃‍♂️ **Quick Setup**

```bash
# 📥 Clone the repository
git clone https://git.supported.systems/MCP/mcp-vultr.git
cd mcp-vultr

# ⚡ Install with uv (recommended)
uv sync --extra dev

# 🧪 Run tests
uv run pytest

# 🎨 Format code  
uv run black src tests && uv run isort src tests

# 🔍 Type checking
uv run mypy src
```

### 📦 **Build & Publish**

```bash
# 🏗️ Build package
uv build

# ✅ Check integrity
uv run twine check dist/*

# 🚀 Publish to PyPI
uv run twine upload dist/*
```

---

## 🤝 **Contributing**

We ❤️ contributions! Whether it's:

- 🐛 **Bug Reports**: Found an issue? Let us know!
- ✨ **Feature Requests**: Have ideas? We want to hear them!
- 📝 **Documentation**: Help make our docs even better
- 🧪 **Testing**: Add tests, improve coverage
- 💻 **Code**: Submit PRs for new features or fixes

### 🚀 **How to Contribute**

1. 🍴 **Fork** the repository
2. 🌿 **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. ✍️ **Make** your changes
4. ✅ **Test** everything (`uv run python run_tests.py --all-checks`)
5. 📝 **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. 📤 **Push** to the branch (`git push origin feature/amazing-feature`)
7. 🎉 **Open** a Pull Request

---

## 📊 **Project Stats**

<div align="center">

| Metric | Value |
|--------|-------|
| 🛠️ **MCP Tools** | **335+** |
| 📦 **Service Modules** | **27** |
| 🐍 **Python Support** | **3.10+** |
| 📈 **Test Coverage** | **90%+** |
| 📚 **Documentation** | **Comprehensive** |
| ⚡ **Performance** | **Production Ready** |

</div>

---

## 🙏 **Acknowledgments**

- 🌩️ **Vultr** for their comprehensive cloud API
- 🤖 **Anthropic** for the Model Context Protocol specification  
- 🐍 **Python Community** for amazing tools and libraries
- 🚀 **FastMCP** for the excellent MCP framework
- 👥 **Contributors** who make this project amazing

---

## 📄 **License**

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ Star us on [GitLab](https://git.supported.systems/MCP/mcp-vultr) if you find Vultr MCP useful!**

Made with ❤️ for the cloud infrastructure community

[🚀 Get Started](#-quick-start) • [📖 Documentation](#-documentation) • [🐛 Report Issues](https://git.supported.systems/MCP/mcp-vultr/issues) • [💬 Discussions](https://git.supported.systems/MCP/mcp-vultr/discussions)

</div>