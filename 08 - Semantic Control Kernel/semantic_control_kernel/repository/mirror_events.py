from __future__ import annotations

from semantic_control_kernel.repository.event_store import MirrorEventStore


class KernelMirrorEventLifecycle:
    def __init__(self, store: MirrorEventStore) -> None:
        self.store = store

    def allow_tools_for_recovery_event(self, mirror_event_id: str, allowed_agent_tools, expires_at: str) -> None:
        self.store.put_tool_availability(mirror_event_id, allowed_agent_tools, expires_at)

    def expire_recovery_tools(self, mirror_event_id: str, reason: str):
        return self.store.mark_event_scoped_tools_expired(mirror_event_id, reason)

    def get_tool_availability(self, mirror_event_id: str):
        return self.store.get_tool_availability(mirror_event_id)
