"""
Database Analysis utilities for Vultr Managed Databases.

This module provides custom analysis functionality that is separate from
the core Vultr API implementation. It uses the Vultr API to gather data
but performs analysis and setup automation locally.
"""

import secrets
import string
from typing import Any


class DatabaseAnalyzer:
    """Custom database analysis functionality for Vultr managed databases."""

    def __init__(self, vultr_client):
        """Initialize with a Vultr database client."""
        self.vultr_client = vultr_client

    async def setup_mysql_database(
        self,
        region: str,
        plan: str,
        label: str,
        root_password: str = None,
        app_user: str = "appuser",
        app_password: str = None,
        app_database: str = "appdb",
    ) -> dict[str, Any]:
        """Quick setup for a MySQL database with application user and database.

        Args:
            region: Region code
            plan: Plan ID
            label: Label for the database
            root_password: Root password (auto-generated if not provided)
            app_user: Application username to create
            app_password: Application user password (auto-generated if not provided)
            app_database: Application database name to create

        Returns:
            Complete setup information including connection details
        """
        try:
            # Generate passwords if not provided
            if not root_password:
                root_password = self._generate_secure_password()
            if not app_password:
                app_password = self._generate_secure_password()

            # Create the MySQL database instance
            database = await self.vultr_client.create_managed_database(
                engine="mysql",
                region=region,
                plan=plan,
                label=label,
                database_engine_version="8",
                vpc_id=None,
                mysql_sql_modes=[],
                mysql_require_primary_key=True,
                mysql_slow_query_log=True,
                mysql_long_query_time=5,
                public_host="",
                trusted_ips=[],
                cluster_time_zone="UTC",
                mysql_root_password=root_password,
            )

            database_id = database.get("id")

            # Wait for database to be ready (this would need proper status checking)
            setup_status = {
                "database_id": database_id,
                "database_label": label,
                "engine": "MySQL 8.0",
                "region": region,
                "plan": plan,
                "status": "provisioning",
                "connection_info": {
                    "host": database.get("host", "pending"),
                    "port": database.get("port", 3306),
                    "username": "root",
                    "password": root_password,
                    "database": "mysql",
                },
                "application_setup": {
                    "app_user": app_user,
                    "app_password": app_password,
                    "app_database": app_database,
                    "setup_commands": [
                        f"CREATE DATABASE {app_database};",
                        f"CREATE USER '{app_user}'@'%' IDENTIFIED BY '{app_password}';",
                        f"GRANT ALL PRIVILEGES ON {app_database}.* TO '{app_user}'@'%';",
                        "FLUSH PRIVILEGES;",
                    ],
                },
                "next_steps": [
                    "Wait for database to finish provisioning",
                    f"Connect as root and create application user '{app_user}'",
                    f"Create application database '{app_database}'",
                    "Configure your application with the connection details",
                    "Consider setting up SSL connections for security",
                ],
                "connection_examples": {
                    "mysql_cli": f"mysql -h {database.get('host', 'HOST')} -u {app_user} -p{app_password} {app_database}",
                    "python": f"mysql:///{app_user}:{app_password}@{database.get('host', 'HOST')}:{database.get('port', 3306)}/{app_database}",
                    "django": {
                        "ENGINE": "django.db.backends.mysql",
                        "NAME": app_database,
                        "USER": app_user,
                        "PASSWORD": app_password,
                        "HOST": database.get("host", "HOST"),
                        "PORT": database.get("port", 3306),
                    },
                },
            }

            return setup_status

        except Exception as e:
            return {
                "error": str(e),
                "recommendations": [
                    "Check that the region and plan are valid",
                    "Ensure sufficient account balance for database creation",
                    "Verify API permissions for database management",
                ],
            }

    async def setup_postgresql_database(
        self,
        region: str,
        plan: str,
        label: str,
        version: str = "17",
        app_user: str = "appuser",
        app_password: str = None,
        app_database: str = "appdb",
    ) -> dict[str, Any]:
        """Quick setup for a PostgreSQL database with application user and database.

        Args:
            region: Region code
            plan: Plan ID
            label: Label for the database
            version: PostgreSQL version (13-17)
            app_user: Application username to create
            app_password: Application user password (auto-generated if not provided)
            app_database: Application database name to create

        Returns:
            Complete setup information including connection details
        """
        try:
            # Generate password if not provided
            if not app_password:
                app_password = self._generate_secure_password()

            # Create the PostgreSQL database instance
            database = await self.vultr_client.create_managed_database(
                engine="pg",
                region=region,
                plan=plan,
                label=label,
                database_engine_version=version,
                vpc_id=None,
                public_host="",
                trusted_ips=[],
                cluster_time_zone="UTC",
            )

            database_id = database.get("id")

            setup_status = {
                "database_id": database_id,
                "database_label": label,
                "engine": f"PostgreSQL {version}",
                "region": region,
                "plan": plan,
                "status": "provisioning",
                "connection_info": {
                    "host": database.get("host", "pending"),
                    "port": database.get("port", 5432),
                    "username": "postgres",
                    "database": "postgres",
                },
                "application_setup": {
                    "app_user": app_user,
                    "app_password": app_password,
                    "app_database": app_database,
                    "setup_commands": [
                        f"CREATE DATABASE {app_database};",
                        f"CREATE USER {app_user} WITH PASSWORD '{app_password}';",
                        f"GRANT ALL PRIVILEGES ON DATABASE {app_database} TO {app_user};",
                        f"\\c {app_database}",
                        f"GRANT ALL ON SCHEMA public TO {app_user};",
                    ],
                },
                "next_steps": [
                    "Wait for database to finish provisioning",
                    f"Connect as postgres and create application user '{app_user}'",
                    f"Create application database '{app_database}'",
                    "Configure your application with the connection details",
                    "Consider setting up SSL connections for security",
                    "Set up regular backups and monitoring",
                ],
                "connection_examples": {
                    "psql": f"psql -h {database.get('host', 'HOST')} -U {app_user} -d {app_database}",
                    "python": f"postgresql://{app_user}:{app_password}@{database.get('host', 'HOST')}:{database.get('port', 5432)}/{app_database}",
                    "django": {
                        "ENGINE": "django.db.backends.postgresql",
                        "NAME": app_database,
                        "USER": app_user,
                        "PASSWORD": app_password,
                        "HOST": database.get("host", "HOST"),
                        "PORT": database.get("port", 5432),
                    },
                    "sqlalchemy": f"postgresql+psycopg2://{app_user}:{app_password}@{database.get('host', 'HOST')}:{database.get('port', 5432)}/{app_database}",
                },
            }

            return setup_status

        except Exception as e:
            return {
                "error": str(e),
                "recommendations": [
                    "Check that the region and plan are valid",
                    "Verify PostgreSQL version is supported",
                    "Ensure sufficient account balance for database creation",
                    "Verify API permissions for database management",
                ],
            }

    async def analyze_database_migration_status(
        self, database_id: str
    ) -> dict[str, Any]:
        """Get the status of an ongoing database migration with detailed analysis.

        Args:
            database_id: The database ID or label

        Returns:
            Migration status information with recommendations
        """
        try:
            # Get migration status from Vultr API
            migration_status = await self.vultr_client.get_migration_status(database_id)
            database_info = await self.vultr_client.get_managed_database(database_id)

            analysis = {
                "database_id": database_id,
                "database_label": database_info.get("label"),
                "migration_status": migration_status.get("status", "unknown"),
                "progress_percentage": migration_status.get("progress", 0),
                "estimated_completion": migration_status.get("estimated_completion"),
                "current_phase": migration_status.get("current_phase", "unknown"),
                "recommendations": [],
                "troubleshooting": [],
            }

            # Analyze migration status and provide recommendations
            status = analysis["migration_status"].lower()

            if status == "running":
                analysis["recommendations"].extend(
                    [
                        "Migration is in progress - avoid making schema changes",
                        "Monitor source database performance during migration",
                        "Prepare for application cutover planning",
                    ]
                )
            elif status == "completed":
                analysis["recommendations"].extend(
                    [
                        "Migration completed successfully",
                        "Verify data integrity on destination database",
                        "Update application connection strings",
                        "Monitor new database performance",
                    ]
                )
            elif status == "failed":
                analysis["recommendations"].extend(
                    [
                        "Migration failed - check error logs",
                        "Verify source database connectivity",
                        "Check destination database capacity",
                        "Consider restarting migration after addressing issues",
                    ]
                )
                analysis["troubleshooting"].extend(
                    [
                        "Check source database permissions",
                        "Verify network connectivity between source and destination",
                        "Ensure sufficient disk space on destination",
                        "Review migration logs for specific error messages",
                    ]
                )

            return analysis

        except Exception as e:
            return {
                "database_id": database_id,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze migration status - check database access"
                ],
            }

    def _generate_secure_password(self, length: int = 16) -> str:
        """Generate a secure random password."""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(characters) for _ in range(length))

        # Ensure password has at least one of each character type
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)
        if not any(c in "!@#$%^&*" for c in password):
            password = password[:-1] + secrets.choice("!@#$%^&*")

        return password

    async def analyze_database_performance(self, database_id: str) -> dict[str, Any]:
        """Analyze database performance and provide optimization recommendations.

        Args:
            database_id: The database ID or label

        Returns:
            Performance analysis with optimization recommendations
        """
        try:
            # Get database info and usage statistics
            database_info = await self.vultr_client.get_managed_database(database_id)
            usage_stats = await self.vultr_client.get_usage(database_id)

            analysis = {
                "database_id": database_id,
                "database_label": database_info.get("label"),
                "engine": database_info.get("database_engine"),
                "plan": database_info.get("plan"),
                "performance_metrics": usage_stats,
                "health_score": 0,
                "bottlenecks": [],
                "recommendations": [],
            }

            # Analyze performance metrics
            cpu_usage = usage_stats.get("cpu_usage", 0)
            memory_usage = usage_stats.get("memory_usage", 0)
            disk_usage = usage_stats.get("disk_usage", 0)

            # Calculate health score
            health_factors = []

            if cpu_usage < 70:
                health_factors.append(25)
            elif cpu_usage < 85:
                health_factors.append(15)
                analysis["bottlenecks"].append("High CPU usage detected")
            else:
                health_factors.append(5)
                analysis["bottlenecks"].append(
                    "Critical CPU usage - immediate attention needed"
                )

            if memory_usage < 80:
                health_factors.append(25)
            elif memory_usage < 90:
                health_factors.append(15)
                analysis["bottlenecks"].append("High memory usage detected")
            else:
                health_factors.append(5)
                analysis["bottlenecks"].append(
                    "Critical memory usage - risk of OOM errors"
                )

            if disk_usage < 70:
                health_factors.append(25)
            elif disk_usage < 85:
                health_factors.append(15)
                analysis["bottlenecks"].append("High disk usage detected")
            else:
                health_factors.append(5)
                analysis["bottlenecks"].append(
                    "Critical disk usage - immediate cleanup needed"
                )

            # Connection performance
            health_factors.append(25)  # Assume good connection performance

            analysis["health_score"] = sum(health_factors)

            # Generate recommendations based on analysis
            analysis["recommendations"] = self._generate_performance_recommendations(
                cpu_usage,
                memory_usage,
                disk_usage,
                database_info.get("database_engine"),
            )

            return analysis

        except Exception as e:
            return {
                "database_id": database_id,
                "error": str(e),
                "recommendations": [
                    "Unable to analyze database performance - check database access"
                ],
            }

    def _generate_performance_recommendations(
        self, cpu_usage: float, memory_usage: float, disk_usage: float, engine: str
    ) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # CPU recommendations
        if cpu_usage > 85:
            recommendations.append(
                "Critical: CPU usage is very high - consider upgrading to a larger plan"
            )
            recommendations.append("Review slow queries and optimize database indices")
        elif cpu_usage > 70:
            recommendations.append("CPU usage is elevated - monitor query performance")

        # Memory recommendations
        if memory_usage > 90:
            recommendations.append(
                "Critical: Memory usage is very high - upgrade plan or optimize queries"
            )
        elif memory_usage > 80:
            recommendations.append("Memory usage is high - consider query optimization")

        # Disk recommendations
        if disk_usage > 85:
            recommendations.append(
                "Critical: Disk usage is very high - clean up old data or upgrade storage"
            )
        elif disk_usage > 70:
            recommendations.append(
                "Disk usage is elevated - plan for capacity expansion"
            )

        # Engine-specific recommendations
        if engine and "mysql" in engine.lower():
            recommendations.extend(
                [
                    "Consider enabling query cache for frequently accessed data",
                    "Review MySQL slow query log for optimization opportunities",
                    "Consider setting up read replicas for read-heavy workloads",
                ]
            )
        elif engine and "pg" in engine.lower():
            recommendations.extend(
                [
                    "Consider running VACUUM ANALYZE for query optimization",
                    "Review PostgreSQL statistics for index usage",
                    "Consider connection pooling for high-concurrency applications",
                ]
            )

        # General recommendations
        if not recommendations:
            recommendations.append("Database performance appears healthy")

        recommendations.extend(
            [
                "Set up monitoring and alerting for proactive management",
                "Schedule regular backups and test restore procedures",
                "Consider read replicas for scaling read operations",
            ]
        )

        return recommendations
