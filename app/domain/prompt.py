from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptSpec:
    mode: str
    language: str
    system_message: str
    user_prompt: str
