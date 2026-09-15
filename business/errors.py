class BusinessCheckError(AssertionError):
    """A case failed; another case's success must not suppress this result."""


class ConfigurationError(ValueError):
    """The case cannot be run with a verified contract."""
