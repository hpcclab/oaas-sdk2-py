"""
OaaS SDK Configuration

This module provides unified configuration for the OaaS SDK
simplified interface with backward compatibility.
"""

from typing import Optional

from pydantic import HttpUrl, Field
from pydantic_settings import BaseSettings

from ..config import OprcConfig


class OaasConfig(BaseSettings):
    """
    Unified configuration object for OaaS SDK.
    
    This class provides a cleaner interface for configuration while
    maintaining compatibility with the existing OprcConfig.
    """
    
    # Core server configuration
    server_url: HttpUrl = Field(default="http://localhost:10000", description="OaaS data manager URL")
    peers: Optional[str] = Field(default=None, description="Comma-separated list of Zenoh peers")
    default_partition: int = Field(default=0, description="Default partition ID")
    
    # Operational modes
    mock_mode: bool = Field(default=False, description="Enable mock mode for testing")
    async_mode: bool = Field(default=True, description="Enable async mode by default")
    
    # Performance settings
    auto_commit: bool = Field(default=True, description="Enable automatic transaction commits")
    batch_size: int = Field(default=100, description="Batch size for bulk operations")
    
    def to_oprc_config(self) -> OprcConfig:
        """Convert to legacy OprcConfig for backward compatibility."""
        return OprcConfig(
            oprc_odgm_url=self.server_url,
            oprc_zenoh_peers=self.peers,
            oprc_partition_default=self.default_partition
        )
    
    def get_zenoh_peers(self) -> Optional[list[str]]:
        """Get Zenoh peers as a list."""
        if self.peers is None:
            return None
        return self.peers.split(",")
