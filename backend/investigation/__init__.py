"""Investigation package exports lightweight schema by default.

Avoid importing the pipeline at module import time so the backend can still boot
in simulated mode on machines where LangGraph or related dependencies are not
installed yet.
"""

from .schema import EvidenceItem, EvidencePool, InvestigationRequest

__all__ = ["InvestigationRequest", "EvidencePool", "EvidenceItem"]
