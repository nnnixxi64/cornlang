from abc import ABC, abstractmethod
from typing import Any

from .ast_nodes import (
    AstNode, UnsafeNode, ImportNode, ExpressionNode, VariableNode,
    FunctionCallNode, BindingNode, NullNode, NumberNode, StringNode,
    BooleanNode, BlockNode, DefArgumentNode, NativeArgumentNode,
    ReturnNode, FunctionDefNode, IfNode, DoWhileNode, WhileNode,
    BreakNode, ContinueNode, AsNode,
)


class AstVisitor(ABC):
    @abstractmethod
    def visit_unsafe_node(self, node: UnsafeNode) -> Any:
        pass

    @abstractmethod
    def visit_import_node(self, node: ImportNode) -> Any:
        pass

    @abstractmethod
    def visit_expression_node(self, node: ExpressionNode) -> Any:
        pass

    @abstractmethod
    def visit_variable_node(self, node: VariableNode) -> Any:
        pass

    @abstractmethod
    def visit_function_call_node(self, node: FunctionCallNode) -> Any:
        pass

    @abstractmethod
    def visit_binding_node(self, node: BindingNode) -> Any:
        pass

    @abstractmethod
    def visit_null_node(self, node: NullNode) -> Any:
        pass

    @abstractmethod
    def visit_number_node(self, node: NumberNode) -> Any:
        pass

    @abstractmethod
    def visit_string_node(self, node: StringNode) -> Any:
        pass

    @abstractmethod
    def visit_boolean_node(self, node: BooleanNode) -> Any:
        pass

    @abstractmethod
    def visit_block_node(self, node: BlockNode) -> Any:
        pass

    @abstractmethod
    def visit_def_argument_node(self, node: DefArgumentNode) -> Any:
        pass

    @abstractmethod
    def visit_native_argument_node(self, node: NativeArgumentNode) -> Any:
        pass

    @abstractmethod
    def visit_return_node(self, node: ReturnNode) -> Any:
        pass

    @abstractmethod
    def visit_function_def_node(self, node: FunctionDefNode) -> Any:
        pass

    @abstractmethod
    def visit_if_node(self, node: IfNode) -> Any:
        pass

    @abstractmethod
    def visit_do_while_node(self, node: DoWhileNode) -> Any:
        pass

    @abstractmethod
    def visit_while_node(self, node: WhileNode) -> Any:
        pass

    @abstractmethod
    def visit_break_node(self, node: BreakNode) -> Any:
        pass

    @abstractmethod
    def visit_continue_node(self, node: ContinueNode) -> Any:
        pass

    @abstractmethod
    def visit_as_node(self, node: AsNode) -> Any:
        pass

    def visit(self, node: AstNode) -> Any:
        match node:
            case UnsafeNode():
                return self.visit_unsafe_node(node)
            case ImportNode():
                return self.visit_import_node(node)
            case ExpressionNode():
                return self.visit_expression_node(node)
            case VariableNode():
                return self.visit_variable_node(node)
            case FunctionCallNode():
                return self.visit_function_call_node(node)
            case BindingNode():
                return self.visit_binding_node(node)
            case NullNode():
                return self.visit_null_node(node)
            case NumberNode():
                return self.visit_number_node(node)
            case StringNode():
                return self.visit_string_node(node)
            case BooleanNode():
                return self.visit_boolean_node(node)
            case BlockNode():
                return self.visit_block_node(node)
            case FunctionDefNode():
                return self.visit_function_def_node(node)
            case ReturnNode():
                return self.visit_return_node(node)
            case IfNode():
                return self.visit_if_node(node)
            case DoWhileNode():
                return self.visit_do_while_node(node)
            case WhileNode():
                return self.visit_while_node(node)
            case BreakNode():
                return self.visit_break_node(node)
            case ContinueNode():
                return self.visit_continue_node(node)
            case AsNode():
                return self.visit_as_node(node)
        return None
