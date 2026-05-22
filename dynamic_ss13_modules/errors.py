class DynamicModulesError(Exception):
    """Base exception for user-facing Dynamic Modules failures."""


class ValidationError(DynamicModulesError):
    """Raised when host config or module manifests are invalid."""


class ResolveError(DynamicModulesError):
    """Raised when module dependencies cannot be resolved."""


class BuildError(DynamicModulesError):
    """Raised when generated build output cannot be produced."""


class GitError(DynamicModulesError):
    """Raised when a git operation fails."""

