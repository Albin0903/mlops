from dataclasses import dataclass
from enum import Enum


class AnalysisMode(str, Enum):
    DOC = "doc"
    QUESTION = "question"


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    content: str
    language: str
    mode: AnalysisMode
    provider: str
    question: str | None = None
