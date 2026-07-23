import os
from llvmlite import binding
from typing import TextIO, Optional

from .mangler import Mangler
from .symbol_table import SymbolTable, Symbol, Variable, Function
from ..ast.ast_nodes import (
    AstNode, UnsafeNode, ImportNode, ExpressionNode, VariableNode,
    FunctionCallNode, BindingNode, NullNode, NumberNode, StringNode,
    BooleanNode, BlockNode, DefArgumentNode, NativeArgumentNode,
    ReturnNode, FunctionDefNode, IfNode, WhileNode, BreakNode,
    ContinueNode, AsNode,
)
from ..ast.ast_visitor import AstVisitor
from ..error import CornError
from ..lexer import TokenType
from ..parser import Parser

BUILTIN_TYPES: list[str] = [
    'boolean', 'int', 'int32', 'int64',
    'float', 'float32', 'double', 'float64',
    'void', 'char', 'string',
]

ARITHMETIC_OPS: tuple[TokenType, ...] = (
    TokenType.PLUS, TokenType.MINUS, TokenType.TIMES,
    TokenType.DIVIDE, TokenType.MOD, TokenType.TILDE,
)


class SemanticVisitor(AstVisitor):
    def __init__(self) -> None:
        self.mangler: Mangler = Mangler()
        self.current_module_name: str = ''
        self.imported_modules: list[str] = []
        self.symbol_table: SymbolTable = SymbolTable()
        self.natives: list[str] = []
        self.in_unsafe_ctx: bool = False

    def visit_null_node(self, node: NullNode) -> NullNode:
        return node

    def visit_number_node(self, node: NumberNode) -> NumberNode:
        return node

    def visit_string_node(self, node: StringNode) -> StringNode:
        return node

    def visit_boolean_node(self, node: BooleanNode) -> BooleanNode:
        return node

    def visit_native_argument_node(self, node: NativeArgumentNode) -> NativeArgumentNode:
        return node

    def visit_break_node(self, node: BreakNode) -> BreakNode:
        return node

    def visit_continue_node(self, node: ContinueNode) -> ContinueNode:
        return node

    def visit_unsafe_node(self, node: UnsafeNode) -> BlockNode:
        self.in_unsafe_ctx = True
        nodes: list[AstNode] = [self.visit(n) for n in node.body.nodes]
        self.in_unsafe_ctx = False
        return BlockNode(nodes)

    def _parse_file(self, file: TextIO) -> BlockNode:
        subparser: Parser = Parser(file)
        return BlockNode(subparser.parse())

    def _visit_module(self, module_name: str, module: BlockNode) -> BlockNode:
        self.current_module_name = module_name
        nodes: list[AstNode] = [self.visit(n) for n in module.nodes]
        self.current_module_name = ''
        return BlockNode(nodes)

    def try_import_stdlib(self, module_name: str) -> Optional[BlockNode]:
        STDLIB_PATH: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'stdlib')
        if not os.path.exists(STDLIB_PATH):
            return None
        module_path: str = STDLIB_PATH + '/' + module_name + '.cn'
        if not os.path.isfile(module_path):
            return None
        self.imported_modules.append(module_name)
        with open(module_path) as file:
            return self._parse_file(file)

    def try_import_current(self, module_name: str) -> Optional[BlockNode]:
        original_module_name: str = module_name
        module_name = original_module_name.replace('.', '/')
        module_path_cn: str = module_name + '.cn'
        module_path_emoji: str = module_name + '.🌽'
        if os.path.exists(module_path_cn) and os.path.isfile(module_path_cn):
            module_path: str = module_path_cn
        elif os.path.exists(module_path_emoji) and os.path.isfile(module_path_emoji):
            module_path = module_path_emoji
        else:
            return None
        self.imported_modules.append(original_module_name)
        with open(module_path) as file:
            return self._parse_file(file)

    def try_import_shared(self, module_name: str) -> bool:
        if not os.path.exists(module_name) or not os.path.isfile(module_name):
            return False
        binding.load_library_permanently(module_name)
        return True

    def visit_import_node(self, node: ImportNode) -> BlockNode:
        module_name: str = node.module_name
        if module_name in self.imported_modules:
            return BlockNode([])
        module: Optional[BlockNode] = self.try_import_stdlib(module_name)
        if not module:
            module = self.try_import_current(module_name)
        if not module and self.in_unsafe_ctx:
            if self.try_import_shared(module_name):
                return BlockNode([])
        if not module:
            ext: str = module_name.split('.')[-1]
            if ext in ('dll', 'so', 'dylib'):
                raise CornError(
                    f"Cannot find module '{module_name}' (need to import shared libraries inside an unsafe context)")
            raise CornError(f"Cannot find module '{module_name}'")
        return self._visit_module(module_name, module)

    def _type_of_literal(self, node: AstNode) -> str:
        match node:
            case NullNode():
                raise CornError("Cannot infer type of null literal")
            case NumberNode():
                return 'int' if isinstance(node.value, int) else 'float'
            case StringNode():
                return 'string'
            case BooleanNode():
                return 'boolean'
        raise CornError(f"Cannot infer type of expression: {type(node).__name__}")

    def _type_of_variable(self, node: VariableNode) -> str:
        name: str = self.mangler.mangle_variable_name(node.name, self.current_module_name)
        if not self.symbol_table.has(name):
            raise CornError(f"Use of undeclared variable '{node.name}'")
        symbol = self.symbol_table.get(name)
        assert symbol is not None
        return symbol.type_name

    def _type_of_call(self, node: FunctionCallNode) -> str:
        args_types: list[str] = [self.visit_type(arg) for arg in node.args]
        symbol: Optional[Symbol] = self.symbol_table.get(node.name)
        if symbol is None or not isinstance(symbol, Function):
            raise CornError(f"Call to undeclared function '{node.name}'")
        if symbol.is_native:
            return symbol.type_name
        mangled: str = self.mangler.mangle_function_name(node.name, args_types, node.module_name or '')
        resolved: Optional[Symbol] = self.symbol_table.get(mangled)
        if resolved is None or not isinstance(resolved, Function):
            raise CornError(f"No overload of '{node.name}' matches argument types {args_types}")
        return resolved.type_name

    def _type_of_expression(self, node: ExpressionNode) -> str:
        left_type: str = self.visit_type(node.left)
        right_type: str = self.visit_type(node.right)
        if left_type == right_type and node.op in ARITHMETIC_OPS:
            return left_type
        return 'boolean'

    def visit_type(self, node: AstNode) -> str:
        match node:
            case NullNode() | NumberNode() | StringNode() | BooleanNode():
                return self._type_of_literal(node)
            case VariableNode():
                return self._type_of_variable(node)
            case FunctionCallNode():
                return self._type_of_call(node)
            case ExpressionNode():
                return self._type_of_expression(node)
            case _:
                raise CornError(f"Cannot infer type of expression: {type(node).__name__}")

    def visit_expression_node(self, node: ExpressionNode) -> ExpressionNode:
        node.left = self.visit(node.left)
        node.right = self.visit(node.right)
        return node

    def visit_variable_node(self, node: VariableNode) -> VariableNode:
        node.name = self.mangler.mangle_variable_name(node.name, self.current_module_name)
        return node

    def visit_function_call_node(self, node: FunctionCallNode) -> FunctionCallNode:
        args_types: list[str] = [self.visit_type(arg) for arg in node.args]
        node.args = [self.visit(arg) for arg in node.args]
        is_native: bool = node.name in self.natives
        if not is_native:
            node.name = self.mangler.mangle_function_name(node.name, args_types, node.module_name or '')
        symbol: Optional[Symbol] = self.symbol_table.get(node.name)
        if symbol is None or not isinstance(symbol, Function):
            raise CornError(f"Call to undeclared function '{node.name}'")
        if symbol.is_unsafe and not self.in_unsafe_ctx:
            raise CornError(f"Call to unsafe function '{node.name}' outside an unsafe context")
        return node

    def _infer_binding_types(self, node: BindingNode) -> str:
        inferred: list[str] = []
        has_explicit_type: bool = node.types is not None and len(node.types) > 0
        last_type: str = ''
        if not has_explicit_type:
            for expr in node.exprs:
                if isinstance(expr, NullNode) and not node.is_nullable:
                    raise CornError("Nullability is prohibited in automatic type inference")
                last_type = self.visit_type(expr)
                inferred.append(last_type)
            node.types = inferred
        else:
            last_type = node.types[0]  # type: ignore[index]
        if last_type not in BUILTIN_TYPES:
            raise CornError(f"Unknown type '{last_type}' in declaration of '{node.names[0]}'")
        return last_type

    def _register_binding_names(self, node: BindingNode, var_type: str, is_mut: bool) -> bool:
        mangled: list[str] = []
        for name in node.names:
            mangled_name: str = self.mangler.mangle_variable_name(name, self.current_module_name)
            sym: Optional[Symbol] = self.symbol_table.get(mangled_name)
            mangled.append(mangled_name)
            if sym is not None and isinstance(sym, Variable):
                if not sym.is_mut:
                    raise CornError(f"Cannot reassign immutable variable '{name}'")
                is_mut = sym.is_mut
            self.symbol_table.set(mangled_name, Variable(var_type, is_mut, node.is_nullable))
        node.names = mangled
        return is_mut

    def _validate_binding_exprs(self, node: BindingNode, is_mut: bool) -> None:
        visited: list[AstNode] = []
        for expr in node.exprs:
            expr = self.visit(expr)
            if hasattr(expr, 'name'):
                symbol: Optional[Symbol] = self.symbol_table.get(expr.name)
                if hasattr(expr, 'asserted') and expr.asserted:
                    pass
                elif symbol and isinstance(symbol, Variable) and not node.is_nullable and symbol.is_nullable:
                    raise CornError("Attempt to assign a nullable expression to a non-nullable variable")
            visited.append(expr)
        node.exprs = visited

    def visit_binding_node(self, node: BindingNode) -> BindingNode:
        var_type: str = self._infer_binding_types(node)
        is_mut: bool = self._register_binding_names(node, var_type, node.is_mut)
        self._validate_binding_exprs(node, is_mut)
        return node

    def visit_block_node(self, node: BlockNode) -> BlockNode:
        return BlockNode([self.visit(n) for n in node.nodes])

    def visit_def_argument_node(self, node: DefArgumentNode) -> DefArgumentNode:
        node.name = self.mangler.mangle_variable_name(node.name, self.current_module_name)
        return node

    def _collect_arg_types(self, args: list[DefArgumentNode]) -> list[str]:
        return [arg.type_name for arg in args]

    def _register_function_params(self, node: FunctionDefNode, is_unsafe: bool, is_nullable: bool) -> None:
        def_args: list[DefArgumentNode] = []
        for arg in node.args:
            assert isinstance(arg, DefArgumentNode)
            mangled: str = self.mangler.mangle_variable_name(arg.name, self.current_module_name)
            self.visit_def_argument_node(arg)
            self.symbol_table.set(mangled, Variable(arg.type_name, is_mut=False, is_nullable=False))
            def_args.append(arg)
        types_list: list[str] = self._collect_arg_types(def_args)
        node.name = self.mangler.mangle_function_name(node.name, types_list, self.current_module_name)
        self.symbol_table.set(node.name,
                              Function(node.type_name, is_unsafe=is_unsafe, is_native=False, is_nullable=is_nullable))

    def _visit_function_body(self, node: FunctionDefNode, is_nullable: bool) -> None:
        visited: list[AstNode] = []
        if node.is_safe:
            self.in_unsafe_ctx = True
        if node.body is not None:
            for inner in node.body.nodes:
                if isinstance(inner, ReturnNode):
                    visited.append(self._visit_return(inner, is_nullable))
                else:
                    visited.append(self.visit(inner))
            node.body = BlockNode(visited)
        if node.is_safe:
            self.in_unsafe_ctx = False

    def _visit_return(self, node: ReturnNode, in_nullable: bool = False) -> ReturnNode:
        if node.expr is not None:
            node.expr = self.visit(node.expr)
            if not in_nullable and isinstance(node.expr, NullNode):
                raise CornError("Attempt to return null in a non-nullable function")
            if not in_nullable and hasattr(node.expr, 'name'):
                symbol: Optional[Symbol] = self.symbol_table.get(node.expr.name)
                if symbol and isinstance(symbol, Variable) and symbol.is_nullable:
                    raise CornError("Attempt to return nullable expression in a non-nullable function")
        return node

    def visit_function_def_node(self, node: FunctionDefNode) -> FunctionDefNode:
        is_native: bool = node.native
        is_unsafe: bool = self.in_unsafe_ctx and not node.is_safe
        is_nullable: bool = node.is_nullable
        if node.type_name not in BUILTIN_TYPES:
            raise CornError(f"Unknown return type '{node.type_name}' in function '{node.name}'")
        if is_native and not self.in_unsafe_ctx:
            raise CornError(f"Declaration of a native function '{node.name}' outside an unsafe context")
        if is_native:
            self.natives.append(node.name)
            self.symbol_table.set(node.name,
                                  Function(node.type_name, is_unsafe=True, is_native=True, is_nullable=False))
        else:
            self._register_function_params(node, is_unsafe, is_nullable)
            self._visit_function_body(node, is_nullable)
        return node

    def visit_return_node(self, node: ReturnNode) -> ReturnNode:
        return self._visit_return(node)

    def visit_if_node(self, node: IfNode) -> IfNode:
        node.condition = self.visit(node.condition)
        node.then = BlockNode([self.visit(child) for child in node.then.nodes])
        if node.otherwise is not None:
            node.otherwise = BlockNode([self.visit(child) for child in node.otherwise.nodes])
        return node

    def visit_while_node(self, node: WhileNode) -> WhileNode:
        node.condition = self.visit(node.condition)
        node.body = BlockNode([self.visit(child) for child in node.body.nodes])
        return node

    def visit_as_node(self, node: AsNode) -> AsNode:
        node.expr = self.visit(node.expr)
        return node
