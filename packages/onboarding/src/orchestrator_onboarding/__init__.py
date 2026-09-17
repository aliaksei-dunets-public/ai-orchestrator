"""Deterministic project onboarding with explicit preview, apply and MCP checks."""

from .onboarding import OnboardingError, apply_plan, build_mcp_config, build_plan, check_task_manager

__all__ = ["OnboardingError", "apply_plan", "build_mcp_config", "build_plan", "check_task_manager"]
