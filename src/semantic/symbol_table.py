from dataclasses import dataclass
from typing import Optional, Union


@dataclass(slots=True)
class Variable:
    type_name: str
    is_mut: bool
    is_nullable: bool


@dataclass(slots=True)
class Function:
    type_name: str
    is_native: bool
    is_unsafe: bool
    is_nullable: bool


Symbol = Union[Variable, Function]


class SymbolTable:
    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]

    def push_scope(self) -> None:
        self.scopes.append({})

    def pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    def define(self, name: str, symbol: Symbol) -> None:
        self.scopes[-1][name] = symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def has(self, name: str) -> bool:
        return self.lookup(name) is not None

    def set(self, name: str, symbol: Symbol) -> None:
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = symbol
                return
        self.scopes[-1][name] = symbol

    def get(self, name: str) -> Optional[Symbol]:
        return self.lookup(name)
