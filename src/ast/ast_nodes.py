from dataclasses import dataclass, field
from typing import Optional, Sequence, Union

from ..lexer import TokenType


class AstNode:
    __slots__ = ()


@dataclass(slots=True)
class ImportNode(AstNode):
    module_name: str


@dataclass(slots=True)
class ExpressionNode(AstNode):
    left: AstNode
    right: AstNode
    op: TokenType


@dataclass(slots=True)
class TypeNode(AstNode):
    name: str


@dataclass(slots=True)
class VariableNode(AstNode):
    module_name: Optional[str]
    name: str
    asserted: bool


@dataclass(slots=True)
class FunctionCallNode(AstNode):
    module_name: Optional[str]
    name: str
    args: list[AstNode]
    asserted: bool


@dataclass(slots=True)
class BindingNode(AstNode):
    names: list[str]
    types: Optional[list[str]]
    exprs: list[AstNode]
    is_mut: bool
    is_nullable: bool


@dataclass(slots=True)
class NullNode(AstNode):
    pass


@dataclass(slots=True)
class NumberNode(AstNode):
    value: Union[int, float]


@dataclass(slots=True)
class StringNode(AstNode):
    value: str


@dataclass(slots=True)
class BooleanNode(AstNode):
    value: bool


@dataclass(slots=True)
class BlockNode(AstNode):
    nodes: list[AstNode]


@dataclass(slots=True)
class UnsafeNode(AstNode):
    body: BlockNode


@dataclass(slots=True)
class DefArgumentNode(AstNode):
    type_name: str
    name: str


@dataclass(slots=True)
class NativeArgumentNode(AstNode):
    type_name: str


@dataclass(slots=True)
class FunctionDefNode(AstNode):
    type_name: str
    name: str
    args: Sequence[AstNode]
    body: Optional[BlockNode]
    native: bool = False
    is_variadic: bool = False
    is_safe: bool = False
    is_nullable: bool = False


@dataclass(slots=True)
class ReturnNode(AstNode):
    expr: Optional[AstNode] = None


@dataclass(slots=True)
class IfNode(AstNode):
    condition: AstNode
    then: BlockNode
    otherwise: Optional[BlockNode] = None


@dataclass(slots=True)
class WhileNode(AstNode):
    condition: AstNode
    body: BlockNode


@dataclass(slots=True)
class BreakNode(AstNode):
    pass


@dataclass(slots=True)
class ContinueNode(AstNode):
    pass


@dataclass(slots=True)
class AsNode(AstNode):
    expr: AstNode
    cast_type: str
