"""Interfaces supplied by target-specific industrial runtime adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ParameterOperation(str, Enum):
    """Operation requested from a device parameter service."""

    READ = "read"
    WRITE = "write"


@dataclass(frozen=True)
class ParameterRequest:
    """Target-neutral request for one numbered device parameter."""

    operation: ParameterOperation
    parameter_number: int
    value: int | float | None = None

    def __post_init__(self) -> None:
        if self.parameter_number < 0:
            raise ValueError("parameter_number must not be negative")
        if self.operation is ParameterOperation.WRITE and self.value is None:
            raise ValueError("a write request requires a value")
        if self.operation is ParameterOperation.READ and self.value is not None:
            raise ValueError("a read request must not supply a value")


class ParameterResultState(str, Enum):
    """Lifecycle state of an asynchronous parameter request."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ParameterResult:
    """Latest result returned for a submitted parameter request."""

    state: ParameterResultState
    value: int | float | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.state is ParameterResultState.FAILED:
            if self.error_code is None:
                raise ValueError("a failed result requires an error_code")
        elif self.error_code is not None or self.error_message is not None:
            raise ValueError("only a failed result may contain error details")


class CyclicIOProvider(Protocol):
    """Exchange raw cyclic images without prescribing a fieldbus runtime."""

    def read_input_image(self) -> bytes:
        """Return the most recently received device-to-controller image."""
        ...

    def write_output_image(self, image: bytes) -> None:
        """Publish one controller-to-device output image."""
        ...


class ParameterService(Protocol):
    """Submit and poll non-blocking device-parameter operations."""

    def submit(self, request: ParameterRequest) -> str:
        """Submit a request and return an adapter-defined correlation ID."""
        ...

    def poll(self, correlation_id: str) -> ParameterResult:
        """Return the current state of a previously submitted request."""
        ...


@dataclass(frozen=True)
class ModuleStatus:
    """Normalized connection status supplied by a module adapter."""

    connected: bool
    enabled: bool
    faulted: bool
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None


class ModuleService(Protocol):
    """Observe and control a configured communication endpoint."""

    def status(self) -> ModuleStatus:
        """Return current normalized module status."""
        ...

    def request_enabled(self, enabled: bool) -> str:
        """Request an enable-state change and return a correlation ID."""
        ...
