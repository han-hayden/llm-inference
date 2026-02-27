"""
Analysis Engine plugin interface.
Current version: stub only. Engines to be implemented in future iterations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from pydantic import BaseModel


class Suggestion(BaseModel):
    category: str       # prefill | decode | cache | latency_tail | general
    severity: str       # critical | warning | info
    title: str
    description: str
    recommendation: str
    metrics_evidence: Dict = {}


class AnalysisResult(BaseModel):
    engine_name: str
    engine_version: str
    task_id: str
    suggestions: List[Suggestion]
    summary: str
    raw_data: Optional[Dict] = None


class AnalysisEngine(ABC):
    """Abstract base class for analysis engine plugins."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    async def analyze(self, task_id: str, summary: dict, records: list) -> AnalysisResult: ...


class AnalysisEngineManager:
    """Registry and executor for analysis engine plugins."""

    def __init__(self):
        self._engines: Dict[str, AnalysisEngine] = {}

    def register(self, engine: AnalysisEngine):
        self._engines[engine.name()] = engine

    def unregister(self, name: str):
        self._engines.pop(name, None)

    def list_engines(self) -> List[str]:
        return list(self._engines.keys())

    async def analyze(
        self, task_id: str, summary: dict, records: list,
        engine_name: str = None,
    ) -> List[AnalysisResult]:
        targets = (
            [self._engines[engine_name]] if engine_name and engine_name in self._engines
            else self._engines.values()
        )
        results = []
        for engine in targets:
            result = await engine.analyze(task_id, summary, records)
            results.append(result)
        return results


engine_manager = AnalysisEngineManager()
