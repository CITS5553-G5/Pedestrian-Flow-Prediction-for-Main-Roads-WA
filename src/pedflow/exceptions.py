"""Project-specific exceptions used at workflow boundaries."""


class PedflowError(Exception):
    """Base class for controlled project workflow failures."""


class ConfigurationError(PedflowError):
    """Raised when a workflow configuration is missing or invalid."""


class ContractError(PedflowError):
    """Raised when an input, feature, or output contract is violated."""


class SourceExecutionError(PedflowError):
    """Raised when a source extractor fails during an integrated run."""
