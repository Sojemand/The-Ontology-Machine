from __future__ import annotations

from phase12_merge_entry_results import ok_result, owner_error


class FakeEmbeddingAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    def create_embeddings(self, request_payload=None):
        self.calls.append("create_embeddings")
        if self.fail:
            return owner_error(
                "create_embeddings",
                [{"code": "embedding_provider_failure", "summary": "Embedding provider failed."}],
            )
        return ok_result("create_embeddings", {"embedding_result": "created"})
