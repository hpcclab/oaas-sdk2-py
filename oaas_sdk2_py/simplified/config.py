"""
OaaS SDK Simplified Configuration

This module re-exports the unified OaasConfig from the main config module.
"""

# Re-export OaasConfig from main config
from ..config import OaasConfig

# For backward compatibility, also export OprcConfig alias
from ..config import OprcConfig

__all__ = ["OaasConfig", "OprcConfig"]
