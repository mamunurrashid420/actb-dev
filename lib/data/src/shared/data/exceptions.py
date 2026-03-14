"""Custom exceptions for the data asset library."""


class DataLibraryError(Exception):
    """Base exception for data asset library errors."""


class AssetNotFoundError(DataLibraryError):
    """Raised when an asset doesn't exist in the specified environment.

    Includes suggestions for similar asset paths when available.
    """

    def __init__(self, asset_path: str, suggestions: list[str] | None = None):
        """Initialize with asset path and optional suggestions.

        Args:
            asset_path: The asset path that was not found
            suggestions: Optional list of similar asset paths
        """
        self.asset_path = asset_path
        self.suggestions = suggestions or []

        message = f"Asset not found: {asset_path}"
        if self.suggestions:
            message += "\n\nDid you mean one of these?\n"
            for suggestion in self.suggestions[:5]:  # Limit to 5 suggestions
                message += f"  - {suggestion}\n"

        super().__init__(message)


class PartitionNotFoundError(DataLibraryError):
    """Raised when a partition doesn't exist for an asset.

    Includes list of available partitions to help users correct their request.
    """

    def __init__(
        self, asset_path: str, partition: str, available: list[str] | None = None
    ):
        """Initialize with partition and available partitions.

        Args:
            asset_path: The asset path
            partition: The partition key that was not found
            available: Optional list of available partition keys
        """
        self.asset_path = asset_path
        self.partition = partition
        self.available = available or []

        message = f"Partition not found: {partition} for asset {asset_path}"
        if self.available:
            message += f"\n\nAvailable partitions ({len(self.available)} total):\n"
            # Show first 10 partitions
            for part in self.available[:10]:
                message += f"  - {part}\n"
            if len(self.available) > 10:
                message += f"  ... and {len(self.available) - 10} more\n"

        super().__init__(message)


class EnvironmentNotFoundError(DataLibraryError):
    """Raised when an environment doesn't exist.

    Includes list of available environments.
    """

    def __init__(self, env_name: str, available: list[str]):
        """Initialize with environment name and available environments.

        Args:
            env_name: The environment name that was not found
            available: List of available environment names
        """
        self.env_name = env_name
        self.available = available

        message = f"Environment not found: {env_name}"
        message += "\n\nAvailable environments:\n"
        for env in available:
            message += f"  - {env}\n"

        super().__init__(message)


class EnvironmentPermissionError(DataLibraryError):
    """Raised when trying to write to an environment without permission.

    Common case: trying to write to production from a notebook.
    """

    def __init__(self, env_name: str, context: str):
        """Initialize with environment and context.

        Args:
            env_name: The environment that doesn't allow writes
            context: Description of current context (e.g., 'notebook', 'pipeline')
        """
        self.env_name = env_name
        self.context = context

        message = (
            f"Cannot write to {env_name} environment from {context} context.\n"
            f"\n"
            f"The {env_name} environment is read-only in this context for safety.\n"
            f"Consider writing to a different environment (e.g., local or dev)."
        )

        super().__init__(message)
