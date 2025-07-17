"""
OaaS SDK Configuration

This module provides unified configuration for the OaaS SDK.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class OaasConfig(BaseSettings):
    """
    Unified configuration object for OaaS SDK.
    
    This class provides a cleaner interface for configuration.
    """
    
    # Core server configuration
    oprc_zenoh_peers: Optional[str] = Field(default=None, description="Comma-separated list of Zenoh peers")
    oprc_partition_default: int = Field(default=0, description="Default partition ID")
    
    # Operational modes
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing")
    async_mode: bool = Field(default=True, description="Enable async mode by default")
    
    # Performance settings
    auto_commit: bool = Field(default=True, description="Enable automatic transaction commits")
    batch_size: int = Field(default=100, description="(DEPRECATED) Batch size for bulk operations")
    
    def get_zenoh_peers(self) -> Optional[list[str]]:
        """Get Zenoh peers as a list."""
        if self.oprc_zenoh_peers is None:
            return None
        return self.oprc_zenoh_peers.split(",")


# For backward compatibility, create an alias
OprcConfig = OaasConfig