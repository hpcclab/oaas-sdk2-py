"""
OaaS SDK Simplified Configuration

This module re-exports the unified OaasConfig from the main config module.
"""

# Re-export OaasConfig from main config
from ..config import OaasConfig

__all__ = ["OaasConfig"]
