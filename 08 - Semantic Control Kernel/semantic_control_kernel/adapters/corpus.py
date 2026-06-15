from __future__ import annotations

from semantic_control_kernel.adapters.base import BasePipelineAdapter
from semantic_control_kernel.adapters.corpus_database_ops import CorpusDatabaseOpsMixin
from semantic_control_kernel.adapters.corpus_rebuild_ops import CorpusRebuildOpsMixin


class CorpusAdapter(CorpusDatabaseOpsMixin, CorpusRebuildOpsMixin, BasePipelineAdapter):
    adapter_name = "CorpusAdapter"
    owner_module = "05 - Corpus Builder"
    owner_contract_module = "corpus_builder.orchestrator_contract"
