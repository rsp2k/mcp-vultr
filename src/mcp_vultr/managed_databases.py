"""
Vultr Managed Databases FastMCP Module.

This module contains FastMCP tools and resources for managing Vultr Managed Databases.
Supports MySQL, PostgreSQL, Valkey (Redis), and Kafka engines with comprehensive
database management features including users, backups, connection pools, and monitoring.
"""

from typing import Any

from fastmcp import FastMCP

from .database_analyzer import DatabaseAnalyzer


def create_managed_databases_mcp(vultr_client) -> FastMCP:
    """
    Create a FastMCP instance for Vultr Managed Databases management.

    Args:
        vultr_client: VultrDNSServer instance

    Returns:
        Configured FastMCP instance with managed database tools
    """
    mcp = FastMCP(name="vultr-managed-databases")
    database_analyzer = DatabaseAnalyzer(vultr_client)

    # Helper function to check if a string looks like a UUID
    def is_uuid_format(s: str) -> bool:
        """Check if a string looks like a UUID."""
        return bool(len(s) == 36 and s.count("-") == 4)

    # Helper function to get database ID from label or UUID
    async def get_database_id(identifier: str) -> str:
        """
        Get the database ID from a label or UUID.

        Args:
            identifier: Database label or UUID

        Returns:
            The database ID (UUID)

        Raises:
            ValueError: If the database is not found
        """
        # If it looks like a UUID, return it as-is
        if is_uuid_format(identifier):
            return identifier

        # Otherwise, search for it by label
        databases = await vultr_client.list_managed_databases()
        for database in databases:
            if database.get("label") == identifier:
                return database["id"]

        raise ValueError(f"Database '{identifier}' not found (searched by label)")

    # Database resources
    @mcp.resource("databases://list")
    async def list_databases_resource() -> list[dict[str, Any]]:
        """List all managed databases in your Vultr account."""
        try:
            return await vultr_client.list_managed_databases()
        except Exception:
            # If the API returns an error when no databases exist, return empty list
            return []

    @mcp.resource("databases://{database_id}")
    async def get_database_resource(database_id: str) -> dict[str, Any]:
        """Get information about a specific managed database.

        Args:
            database_id: The database ID or label
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_managed_database(actual_id)

    @mcp.resource("databases://plans")
    async def list_database_plans_resource() -> list[dict[str, Any]]:
        """List all available managed database plans."""
        return await vultr_client.list_database_plans()

    # Core Database Management Tools
    # Core Database Management Tools

    @mcp.tool
    async def create(
        database_engine: str,
        database_engine_version: str,
        region: str,
        plan: str,
        label: str,
        tag: str | None = None,
        vpc_id: str | None = None,
        trusted_ips: list[str] | None = None,
        mysql_sql_modes: list[str] | None = None,
        mysql_require_primary_key: bool | None = None,
        mysql_slow_query_log: bool | None = None,
        valkey_eviction_policy: str | None = None,
        kafka_rest_enabled: bool | None = None,
        kafka_schema_registry_enabled: bool | None = None,
        kafka_connect_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Create a new managed database.

        Args:
            database_engine: Database engine (mysql, pg, valkey, kafka)
            database_engine_version: Engine version (MySQL: 8, PostgreSQL: 13-17, Valkey: 7, Kafka: 3.8)
            region: Region code (e.g., 'ewr', 'lax')
            plan: Plan ID (e.g., 'vultr-dbaas-hobbyist-cc-1-25-1')
            label: User-supplied label for the database
            tag: Optional tag for the database
            vpc_id: VPC ID to deploy in (or 'new' for new VPC)
            trusted_ips: List of IP addresses allowed to access (CIDR notation)
            mysql_sql_modes: MySQL SQL modes to enable (MySQL only)
            mysql_require_primary_key: Require primary key for tables (MySQL only)
            mysql_slow_query_log: Enable slow query logging (MySQL only)
            valkey_eviction_policy: Data eviction policy (Valkey only)
            kafka_rest_enabled: Enable Kafka REST support (Kafka only, business+ plans)
            kafka_schema_registry_enabled: Enable Schema Registry (Kafka only, business+ plans)
            kafka_connect_enabled: Enable Kafka Connect (Kafka only, business+ plans)

        Returns:
            Created database information
        """
        return await vultr_client.create_managed_database(
            database_engine=database_engine,
            database_engine_version=database_engine_version,
            region=region,
            plan=plan,
            label=label,
            tag=tag,
            vpc_id=vpc_id,
            trusted_ips=trusted_ips,
            mysql_sql_modes=mysql_sql_modes,
            mysql_require_primary_key=mysql_require_primary_key,
            mysql_slow_query_log=mysql_slow_query_log,
            valkey_eviction_policy=valkey_eviction_policy,
            kafka_rest_enabled=kafka_rest_enabled,
            kafka_schema_registry_enabled=kafka_schema_registry_enabled,
            kafka_connect_enabled=kafka_connect_enabled,
        )

    @mcp.tool
    async def update(
        database_id: str,
        region: str | None = None,
        plan: str | None = None,
        label: str | None = None,
        tag: str | None = None,
        vpc_id: str | None = None,
        timezone: str | None = None,
        trusted_ips: list[str] | None = None,
        mysql_sql_modes: list[str] | None = None,
        mysql_require_primary_key: bool | None = None,
        mysql_slow_query_log: bool | None = None,
        valkey_eviction_policy: str | None = None,
        kafka_rest_enabled: bool | None = None,
        kafka_schema_registry_enabled: bool | None = None,
        kafka_connect_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Update a managed database configuration.

        Args:
            database_id: The database ID or label to update
            region: New region (requires migration)
            plan: New plan ID (for scaling)
            label: New label for the database
            tag: New tag for the database
            vpc_id: New VPC ID
            timezone: Database timezone (TZ format, e.g., 'UTC', 'America/New_York')
            trusted_ips: New list of trusted IP addresses (CIDR notation)
            mysql_sql_modes: MySQL SQL modes (MySQL only)
            mysql_require_primary_key: Require primary key setting (MySQL only)
            mysql_slow_query_log: Slow query log setting (MySQL only)
            valkey_eviction_policy: Eviction policy (Valkey only)
            kafka_rest_enabled: Kafka REST setting (Kafka only)
            kafka_schema_registry_enabled: Schema Registry setting (Kafka only)
            kafka_connect_enabled: Kafka Connect setting (Kafka only)

        Returns:
            Updated database information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.update_managed_database(
            database_id=actual_id,
            region=region,
            plan=plan,
            label=label,
            tag=tag,
            vpc_id=vpc_id,
            timezone=timezone,
            trusted_ips=trusted_ips,
            mysql_sql_modes=mysql_sql_modes,
            mysql_require_primary_key=mysql_require_primary_key,
            mysql_slow_query_log=mysql_slow_query_log,
            valkey_eviction_policy=valkey_eviction_policy,
            kafka_rest_enabled=kafka_rest_enabled,
            kafka_schema_registry_enabled=kafka_schema_registry_enabled,
            kafka_connect_enabled=kafka_connect_enabled,
        )

    @mcp.tool
    async def delete(database_id: str) -> dict[str, str]:
        """Delete a managed database.

        Args:
            database_id: The database ID or label (e.g., "my-mysql-db" or UUID)

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.delete_managed_database(actual_id)
        return {
            "status": "success",
            "message": f"Database {database_id} deleted successfully",
        }

    @mcp.tool
    async def get_usage(database_id: str) -> dict[str, Any]:
        """Get database usage statistics (CPU, memory, disk).

        Args:
            database_id: The database ID or label (e.g., "my-mysql-db" or UUID)

        Returns:
            Usage information including CPU, memory, and disk statistics
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_database_usage(actual_id)

    @mcp.tool
    async def analyze_database_performance(database_id: str) -> dict[str, Any]:
        """Analyze database performance and provide optimization recommendations.

        Args:
            database_id: The database ID or label (e.g., "my-mysql-db" or UUID)

        Returns:
            Performance analysis with health score and optimization recommendations
        """
        actual_id = await get_database_id(database_id)
        return await database_analyzer.analyze_database_performance(actual_id)

    # Database User Management Tools
    @mcp.tool
    async def list_users(database_id: str) -> list[dict[str, Any]]:
        """List all users in a managed database.

        Args:
            database_id: The database ID or label (e.g., "my-mysql-db" or UUID)

        Returns:
            List of database users with their permissions
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_database_users(actual_id)

    @mcp.tool
    async def create_user(
        database_id: str,
        username: str,
        password: str | None = None,
        encryption: str | None = None,
        access_level: str | None = None,
    ) -> dict[str, Any]:
        """Create a new database user.

        Args:
            database_id: The database ID or label
            username: Username for the new user
            password: Password (auto-generated if not provided)
            encryption: Password encryption type (MySQL: caching_sha2_password, mysql_native_password)
            access_level: Permission level (Kafka: admin, read, write, readwrite)

        Returns:
            Created user information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.create_database_user(
            database_id=actual_id,
            username=username,
            password=password,
            encryption=encryption,
            access_level=access_level,
        )

    @mcp.tool
    async def get_user(database_id: str, username: str) -> dict[str, Any]:
        """Get information about a specific database user.

        Args:
            database_id: The database ID or label
            username: The username to get information for

        Returns:
            User information including permissions
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_database_user(actual_id, username)

    @mcp.tool
    async def update_user(
        database_id: str,
        username: str,
        password: str | None = None,
        access_level: str | None = None,
    ) -> dict[str, Any]:
        """Update a database user's password or permissions.

        Args:
            database_id: The database ID or label
            username: The username to update
            password: New password
            access_level: New permission level (Kafka only)

        Returns:
            Updated user information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.update_database_user(
            database_id=actual_id,
            username=username,
            password=password,
            access_level=access_level,
        )

    @mcp.tool
    async def delete_user(database_id: str, username: str) -> dict[str, str]:
        """Delete a database user.

        Args:
            database_id: The database ID or label
            username: The username to delete

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.delete_database_user(actual_id, username)
        return {"status": "success", "message": f"User {username} deleted successfully"}

    # Database Access Control (Valkey/Redis)
    @mcp.tool
    async def update_user_access_control(
        database_id: str,
        username: str,
        acl_categories: list[str] | None = None,
        acl_channels: list[str] | None = None,
        acl_commands: list[str] | None = None,
        acl_keys: list[str] | None = None,
    ) -> dict[str, str]:
        """Update access control for a database user (Valkey/Redis only).

        Args:
            database_id: The database ID or label
            username: The username to update
            acl_categories: ACL categories (e.g., ["+@all"])
            acl_channels: ACL channels (e.g., ["*"])
            acl_commands: ACL commands
            acl_keys: ACL keys (e.g., ["*"])

        Returns:
            Status message confirming update
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.update_database_user_access_control(
            database_id=actual_id,
            username=username,
            acl_categories=acl_categories,
            acl_channels=acl_channels,
            acl_commands=acl_commands,
            acl_keys=acl_keys,
        )
        return {
            "status": "success",
            "message": f"Access control updated for user {username}",
        }

    # Database Schema Management
    @mcp.tool
    async def list_databases(database_id: str) -> list[dict[str, Any]]:
        """List logical databases within a managed database instance.

        Args:
            database_id: The database ID or label

        Returns:
            List of logical databases
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_logical_databases(actual_id)

    @mcp.tool
    async def create_logical_database(database_id: str, name: str) -> dict[str, Any]:
        """Create a new logical database within a managed database instance.

        Args:
            database_id: The database ID or label
            name: Name for the new logical database

        Returns:
            Created logical database information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.create_logical_database(actual_id, name)

    @mcp.tool
    async def get_logical_database(database_id: str, db_name: str) -> dict[str, Any]:
        """Get information about a logical database.

        Args:
            database_id: The database ID or label
            db_name: The logical database name

        Returns:
            Logical database information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_logical_database(actual_id, db_name)

    @mcp.tool
    async def delete_logical_database(database_id: str, db_name: str) -> dict[str, str]:
        """Delete a logical database.

        Args:
            database_id: The database ID or label
            db_name: The logical database name to delete

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.delete_logical_database(actual_id, db_name)
        return {
            "status": "success",
            "message": f"Logical database {db_name} deleted successfully",
        }

    # Connection Pool Management
    @mcp.tool
    async def list_connection_pools(database_id: str) -> list[dict[str, Any]]:
        """List connection pools for a managed database.

        Args:
            database_id: The database ID or label

        Returns:
            List of connection pools
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_connection_pools(actual_id)

    @mcp.tool
    async def create_connection_pool(
        database_id: str, name: str, database: str, username: str, mode: str, size: int
    ) -> dict[str, Any]:
        """Create a new connection pool.

        Args:
            database_id: The database ID or label
            name: Connection pool name
            database: Target logical database name
            username: Database username for the pool
            mode: Pool mode (session, transaction, statement)
            size: Pool size (number of connections)

        Returns:
            Created connection pool information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.create_connection_pool(
            database_id=actual_id,
            name=name,
            database=database,
            username=username,
            mode=mode,
            size=size,
        )

    @mcp.tool
    async def get_connection_pool(database_id: str, pool_name: str) -> dict[str, Any]:
        """Get information about a connection pool.

        Args:
            database_id: The database ID or label
            pool_name: The connection pool name

        Returns:
            Connection pool information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_connection_pool(actual_id, pool_name)

    @mcp.tool
    async def update_connection_pool(
        database_id: str,
        pool_name: str,
        database: str | None = None,
        username: str | None = None,
        mode: str | None = None,
        size: int | None = None,
    ) -> dict[str, Any]:
        """Update a connection pool configuration.

        Args:
            database_id: The database ID or label
            pool_name: The connection pool name to update
            database: New target logical database name
            username: New database username
            mode: New pool mode (session, transaction, statement)
            size: New pool size

        Returns:
            Updated connection pool information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.update_connection_pool(
            database_id=actual_id,
            pool_name=pool_name,
            database=database,
            username=username,
            mode=mode,
            size=size,
        )

    @mcp.tool
    async def delete_connection_pool(
        database_id: str, pool_name: str
    ) -> dict[str, str]:
        """Delete a connection pool.

        Args:
            database_id: The database ID or label
            pool_name: The connection pool name to delete

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.delete_connection_pool(actual_id, pool_name)
        return {
            "status": "success",
            "message": f"Connection pool {pool_name} deleted successfully",
        }

    # Backup Management
    @mcp.tool
    async def list_backups(database_id: str) -> list[dict[str, Any]]:
        """List available backups for a managed database.

        Args:
            database_id: The database ID or label

        Returns:
            List of available backups with timestamps and sizes
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_database_backups(actual_id)

    @mcp.tool
    async def restore_from_backup(
        database_id: str,
        backup_label: str,
        database_label: str,
        plan: str,
        region: str,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """Restore a database from a backup to a new instance.

        Args:
            database_id: The source database ID or label
            backup_label: The backup label/timestamp to restore from
            database_label: Label for the new restored database
            plan: Plan ID for the new database
            region: Region for the new database
            vpc_id: VPC ID for the new database

        Returns:
            Information about the restoration process
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.restore_database_from_backup(
            database_id=actual_id,
            backup_label=backup_label,
            database_label=database_label,
            plan=plan,
            region=region,
            vpc_id=vpc_id,
        )

    @mcp.tool
    async def fork_database(
        database_id: str,
        label: str,
        region: str,
        plan: str,
        vpc_id: str | None = None,
    ) -> dict[str, Any]:
        """Fork a database to create a copy.

        Args:
            database_id: The source database ID or label
            label: Label for the forked database
            region: Region for the new database
            plan: Plan ID for the new database
            vpc_id: VPC ID for the new database

        Returns:
            Information about the forked database
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.fork_database(
            database_id=actual_id, label=label, region=region, plan=plan, vpc_id=vpc_id
        )

    # Read Replica Management
    @mcp.tool
    async def create_read_replica(
        database_id: str, label: str, region: str, plan: str
    ) -> dict[str, Any]:
        """Create a read replica of a database.

        Args:
            database_id: The source database ID or label
            label: Label for the read replica
            region: Region for the read replica
            plan: Plan ID for the read replica

        Returns:
            Information about the created read replica
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.create_read_replica(
            database_id=actual_id, label=label, region=region, plan=plan
        )

    @mcp.tool
    async def promote_read_replica(database_id: str) -> dict[str, str]:
        """Promote a read replica to a standalone database.

        Args:
            database_id: The read replica database ID or label

        Returns:
            Status message confirming promotion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.promote_read_replica(actual_id)
        return {
            "status": "success",
            "message": f"Read replica {database_id} promoted successfully",
        }

    # Maintenance and Migration
    @mcp.tool
    async def list_available_versions(
        database_id: str,
    ) -> list[dict[str, Any]]:
        """List available versions for database engine upgrades.

        Args:
            database_id: The database ID or label

        Returns:
            List of available versions for upgrade
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_database_versions(actual_id)

    @mcp.tool
    async def start_version_upgrade(database_id: str, version: str) -> dict[str, str]:
        """Start a database engine version upgrade.

        Args:
            database_id: The database ID or label
            version: Target version to upgrade to

        Returns:
            Status message confirming upgrade start
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.start_version_upgrade(actual_id, version)
        return {
            "status": "success",
            "message": f"Version upgrade to {version} started for {database_id}",
        }

    @mcp.tool
    async def get_maintenance_updates(
        database_id: str,
    ) -> list[dict[str, Any]]:
        """Get available maintenance updates for a database.

        Args:
            database_id: The database ID or label

        Returns:
            List of available maintenance updates
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_maintenance_updates(actual_id)

    @mcp.tool
    async def start_maintenance(database_id: str) -> dict[str, str]:
        """Start maintenance on a database.

        Args:
            database_id: The database ID or label

        Returns:
            Status message confirming maintenance start
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.start_maintenance(actual_id)
        return {
            "status": "success",
            "message": f"Maintenance started for {database_id}",
        }

    @mcp.tool
    async def get_migration_status(database_id: str) -> dict[str, Any]:
        """Get the status of an ongoing database migration.

        Args:
            database_id: The database ID or label

        Returns:
            Migration status information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_migration_status(actual_id)

    @mcp.tool
    async def analyze_database_migration_status(database_id: str) -> dict[str, Any]:
        """Get enhanced migration status analysis with recommendations.

        Args:
            database_id: The database ID or label

        Returns:
            Detailed migration analysis with troubleshooting recommendations
        """
        actual_id = await get_database_id(database_id)
        return await database_analyzer.analyze_database_migration_status(actual_id)

    @mcp.tool
    async def start_migration(
        database_id: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        ssl: bool = True,
    ) -> dict[str, str]:
        """Start migrating data from an external database.

        Args:
            database_id: The destination database ID or label
            host: Source database hostname
            port: Source database port
            username: Source database username
            password: Source database password
            database: Source database name
            ssl: Use SSL connection to source

        Returns:
            Status message confirming migration start
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.start_migration(
            database_id=actual_id,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            ssl=ssl,
        )
        return {"status": "success", "message": f"Migration started for {database_id}"}

    @mcp.tool
    async def stop_migration(database_id: str) -> dict[str, str]:
        """Stop an ongoing database migration.

        Args:
            database_id: The database ID or label

        Returns:
            Status message confirming migration stop
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.stop_migration(actual_id)
        return {"status": "success", "message": f"Migration stopped for {database_id}"}

    # Kafka-specific Tools
    @mcp.tool
    async def list_kafka_topics(database_id: str) -> list[dict[str, Any]]:
        """List Kafka topics (Kafka databases only).

        Args:
            database_id: The Kafka database ID or label

        Returns:
            List of Kafka topics
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.list_kafka_topics(actual_id)

    @mcp.tool
    async def create_kafka_topic(
        database_id: str,
        name: str,
        partitions: int = 3,
        replication: int = 2,
        retention_hours: int = 168,
        retention_bytes: int = 1073741824,
    ) -> dict[str, Any]:
        """Create a Kafka topic (Kafka databases only).

        Args:
            database_id: The Kafka database ID or label
            name: Topic name
            partitions: Number of partitions
            replication: Replication factor
            retention_hours: Retention time in hours
            retention_bytes: Retention size in bytes

        Returns:
            Created topic information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.create_kafka_topic(
            database_id=actual_id,
            name=name,
            partitions=partitions,
            replication=replication,
            retention_hours=retention_hours,
            retention_bytes=retention_bytes,
        )

    @mcp.tool
    async def get_kafka_topic(database_id: str, topic_name: str) -> dict[str, Any]:
        """Get information about a Kafka topic.

        Args:
            database_id: The Kafka database ID or label
            topic_name: The topic name

        Returns:
            Kafka topic information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.get_kafka_topic(actual_id, topic_name)

    @mcp.tool
    async def update_kafka_topic(
        database_id: str,
        topic_name: str,
        partitions: int | None = None,
        replication: int | None = None,
        retention_hours: int | None = None,
        retention_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Update a Kafka topic configuration.

        Args:
            database_id: The Kafka database ID or label
            topic_name: The topic name to update
            partitions: New number of partitions
            replication: New replication factor
            retention_hours: New retention time in hours
            retention_bytes: New retention size in bytes

        Returns:
            Updated topic information
        """
        actual_id = await get_database_id(database_id)
        return await vultr_client.update_kafka_topic(
            database_id=actual_id,
            topic_name=topic_name,
            partitions=partitions,
            replication=replication,
            retention_hours=retention_hours,
            retention_bytes=retention_bytes,
        )

    @mcp.tool
    async def delete_kafka_topic(database_id: str, topic_name: str) -> dict[str, str]:
        """Delete a Kafka topic.

        Args:
            database_id: The Kafka database ID or label
            topic_name: The topic name to delete

        Returns:
            Status message confirming deletion
        """
        actual_id = await get_database_id(database_id)
        await vultr_client.delete_kafka_topic(actual_id, topic_name)
        return {
            "status": "success",
            "message": f"Kafka topic {topic_name} deleted successfully",
        }

    # Helper Setup Tools
    @mcp.tool
    async def list_plans() -> list[dict[str, Any]]:
        """List all available managed database plans.

        Returns:
            List of database plans with pricing and specifications
        """
        return await vultr_client.list_database_plans()

    @mcp.tool
    async def setup_mysql_database(
        region: str,
        plan: str,
        label: str,
        root_password: str | None = None,
        app_user: str = "appuser",
        app_password: str | None = None,
        app_database: str = "appdb",
    ) -> dict[str, Any]:
        """Quick setup for a MySQL database with application user and database.

        Args:
            region: Region code (e.g., 'ewr', 'lax')
            plan: Plan ID (e.g., 'vultr-dbaas-hobbyist-cc-1-25-1')
            label: Label for the database
            root_password: Root password (auto-generated if not provided)
            app_user: Application username to create
            app_password: Application user password (auto-generated if not provided)
            app_database: Application database name to create

        Returns:
            Complete setup information including connection details
        """
        return await database_analyzer.setup_mysql_database(
            region=region,
            plan=plan,
            label=label,
            root_password=root_password,
            app_user=app_user,
            app_password=app_password,
            app_database=app_database,
        )

    @mcp.tool
    async def setup_postgresql_database(
        region: str,
        plan: str,
        label: str,
        version: str = "17",
        app_user: str = "appuser",
        app_password: str | None = None,
        app_database: str = "appdb",
    ) -> dict[str, Any]:
        """Quick setup for a PostgreSQL database with application user and database.

        Args:
            region: Region code (e.g., 'ewr', 'lax')
            plan: Plan ID (e.g., 'vultr-dbaas-hobbyist-cc-1-25-1')
            label: Label for the database
            version: PostgreSQL version (13-17)
            app_user: Application username to create
            app_password: Application user password (auto-generated if not provided)
            app_database: Application database name to create

        Returns:
            Complete setup information including connection details
        """
        return await database_analyzer.setup_postgresql_database(
            region=region,
            plan=plan,
            label=label,
            version=version,
            app_user=app_user,
            app_password=app_password,
            app_database=app_database,
        )

    return mcp
