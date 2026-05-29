class InvalidWorkbookError(ValueError):
    """Uploaded workbook is missing required sheets or columns."""


class ScenarioExtractionError(ValueError):
    """Info sheet cannot be parsed into a scenario table."""


class InvalidChainError(ValueError):
    """Scenario chain is invalid (too short, duplicate indices, out-of-range)."""


class ReportGenerationError(RuntimeError):
    """Something failed during report generation."""
