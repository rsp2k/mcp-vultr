"""
Vultr Startup Scripts FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr startup scripts.
"""

from typing import Any

from fastmcp import Context, FastMCP

from .notification_manager import NotificationManager


def create_startup_scripts_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr startup scripts management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with startup scripts management tools
    """
    mcp = FastMCP(name="vultr-startup-scripts")

    # Helper function to check if string is UUID format
    def is_uuid_format(value: str) -> bool:
        """Check if a string looks like a UUID."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))

    # Helper function to get startup script ID from name or ID
    async def get_startup_script_id(identifier: str) -> str:
        """Get the startup script ID from name or existing ID."""
        if is_uuid_format(identifier):
            return identifier

        scripts = await vultr_client.list_startup_scripts()
        for script in scripts:
            if script.get("name") == identifier:
                return script["id"]

        raise ValueError(f"Startup script '{identifier}' not found")

    @mcp.tool()
    async def list_startup_scripts() -> list[dict[str, Any]]:
        """
        List all startup scripts.

        Returns:
            List of startup scripts
        """
        return await vultr_client.list_startup_scripts()

    @mcp.tool()
    async def get_startup_script(script_identifier: str) -> dict[str, Any]:
        """
        Get details of a specific startup script.
        Smart identifier resolution: use script name or UUID.

        Args:
            script_identifier: The startup script name or ID

        Returns:
            Startup script details
        """
        script_id = await get_startup_script_id(script_identifier)
        return await vultr_client.get_startup_script(script_id)

    @mcp.tool()
    async def create_startup_script(
        name: str, script: str, ctx: Context | None = None, script_type: str = "boot"
    ) -> dict[str, Any]:
        """
        Create a new startup script.

        Args:
            name: Name for the startup script
            script: The script content
            script_type: Type of script ('boot' or 'pxe')

        Returns:
            Created startup script details
        """
        result = await vultr_client.create_startup_script(name, script, script_type)

        # Notify clients that startup script list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_startup_script", script_id=result.get("id")
            )

        return result

    @mcp.tool()
    async def update_startup_script(
        script_identifier: str,
        name: str | None = None,
        script: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """
        Update a startup script.
        Smart identifier resolution: use script name or UUID.

        Args:
            script_identifier: The startup script name or ID
            name: New name for the script
            script: New script content

        Returns:
            Updated startup script details
        """
        script_id = await get_startup_script_id(script_identifier)
        result = await vultr_client.update_startup_script(script_id, name, script)

        # Notify clients that startup script list and specific script have changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="update_startup_script", script_id=script_id
            )

        return result

    @mcp.tool()
    async def delete_startup_script(
        script_identifier: str, ctx: Context | None = None
    ) -> str:
        """
        Delete a startup script.
        Smart identifier resolution: use script name or UUID.

        Args:
            script_identifier: The startup script name or ID to delete

        Returns:
            Success message
        """
        script_id = await get_startup_script_id(script_identifier)
        await vultr_client.delete_startup_script(script_id)

        # Notify clients that startup script list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="delete_startup_script", script_id=script_id
            )

        return f"Successfully deleted startup script {script_identifier}"

    @mcp.tool()
    async def list_boot_scripts() -> list[dict[str, Any]]:
        """
        List boot startup scripts.

        Returns:
            List of boot startup scripts
        """
        all_scripts = await vultr_client.list_startup_scripts()
        boot_scripts = [
            script for script in all_scripts if script.get("type", "").lower() == "boot"
        ]
        return boot_scripts

    @mcp.tool()
    async def list_pxe_scripts() -> list[dict[str, Any]]:
        """
        List PXE startup scripts.

        Returns:
            List of PXE startup scripts
        """
        all_scripts = await vultr_client.list_startup_scripts()
        pxe_scripts = [
            script for script in all_scripts if script.get("type", "").lower() == "pxe"
        ]
        return pxe_scripts

    @mcp.tool()
    async def search_startup_scripts(query: str) -> list[dict[str, Any]]:
        """
        Search startup scripts by name or content.

        Args:
            query: Search term to look for in script names or content

        Returns:
            List of matching startup scripts
        """
        all_scripts = await vultr_client.list_startup_scripts()
        matching_scripts = []

        for script in all_scripts:
            name = script.get("name", "").lower()
            content = script.get("script", "").lower()

            if query.lower() in name or query.lower() in content:
                matching_scripts.append(script)

        return matching_scripts

    @mcp.tool()
    async def create_common_startup_script(
        script_type: str, ctx: Context | None = None, ssh_port: int = 22
    ) -> dict[str, Any]:
        """
        Create a common startup script from templates.

        Args:
            script_type: Type of script ('docker_install', 'nodejs_install', 'security_updates', 'ssh_setup')
            ssh_port: SSH port to use for 'ssh_setup' script type (default: 22)

        Returns:
            Created startup script details
        """
        templates = {
            "docker_install": {
                "name": "Docker Installation",
                "script": """#!/bin/bash
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
usermod -aG docker $USER
""",
            },
            "nodejs_install": {
                "name": "Node.js Installation",
                "script": """#!/bin/bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
apt-get install -y nodejs
npm install -g pm2
""",
            },
            "security_updates": {
                "name": "Security Updates",
                "script": """#!/bin/bash
apt-get update
apt-get upgrade -y
apt-get install -y unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades
""",
            },
            "ssh_setup": {
                "name": "SSH Hardening",
                "script": f"""#!/bin/bash
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#Port 22/Port {ssh_port}/' /etc/ssh/sshd_config
systemctl restart sshd
""",
            },
        }

        if script_type not in templates:
            raise ValueError(
                f"Unknown script type: {script_type}. Available: {list(templates.keys())}"
            )

        template = templates[script_type]
        result = await vultr_client.create_startup_script(
            template["name"], template["script"], "boot"
        )

        # Notify clients that startup script list has changed
        if ctx is not None:
            await NotificationManager.notify_resource_change(
                ctx=ctx, operation="create_startup_script", script_id=result.get("id")
            )

        return result

    @mcp.tool()
    async def get_startup_script_content(script_identifier: str) -> str:
        """
        Get the content of a startup script.
        Smart identifier resolution: use script name or UUID.

        Args:
            script_identifier: The startup script name or ID

        Returns:
            Script content
        """
        script = await get_startup_script(script_identifier)
        return script.get("script", "")

    return mcp
