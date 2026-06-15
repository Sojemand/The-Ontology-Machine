from __future__ import annotations

from typing import Protocol

from semantic_control_kernel.types.client_frontend_events import ClientFrontendEvent, ClientFrontendEventAck


class ClientFrontendEventSink(Protocol):
    def emit(self, event: ClientFrontendEvent) -> ClientFrontendEventAck:
        """Emit one Kernel-owned Client Frontend event to the configured host surface."""
