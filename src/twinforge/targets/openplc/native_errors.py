"""Exceptions shared by native OpenPLC target collaborators."""


class OpenPLCNativeUnsupportedError(ValueError):
    """Raised when source behavior exceeds the evidenced native subset."""
