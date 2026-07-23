from dataclasses import dataclass, field

from .token_type import TokenType


@dataclass(slots=True)
class Token:
    type: TokenType
    line: int
    col: int
    value: str = ""
