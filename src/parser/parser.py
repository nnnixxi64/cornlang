from typing import TextIO, Optional

from ..ast.ast_nodes import (
    AstNode, ExpressionNode, VariableNode, FunctionCallNode, BindingNode,
    NullNode, NumberNode, StringNode, BooleanNode, BlockNode, UnsafeNode,
    DefArgumentNode, NativeArgumentNode, ReturnNode, FunctionDefNode,
    IfNode, WhileNode, BreakNode, ContinueNode, AsNode, ImportNode,
)
from ..error import CornError
from ..lexer import Lexer, Token, TokenType


class Parser:
    def __init__(self, file: TextIO):
        self.lexer: Lexer = Lexer(file)
        self.current: Token = self.lexer.next_token()
        self.lookahead: Token = self.lexer.next_token()

    def next_token(self) -> Token:
        self.current = self.lookahead
        self.lookahead = self.lexer.next_token()
        return self.current

    def expect(self, token_type: TokenType) -> None:
        if self.current.type != token_type:
            raise CornError(f"Unexpected symbol at line {self.current.line} col {self.current.col}")
        self.next_token()

    def parse_additive(self) -> AstNode:
        left: AstNode = self.parse_multiplicative()
        while self.current.type in (TokenType.PLUS, TokenType.MINUS):
            op: TokenType = self.current.type
            self.next_token()
            right: AstNode = self.parse_multiplicative()
            left = ExpressionNode(left, right, op)
        return left

    def parse_multiplicative(self) -> AstNode:
        left: AstNode = self.parse_primary()
        while self.current.type in (TokenType.TIMES, TokenType.DIVIDE, TokenType.MOD, TokenType.TILDE):
            op: TokenType = self.current.type
            self.next_token()
            right: AstNode = self.parse_primary()
            left = ExpressionNode(left, right, op)
        return left

    def parse_primary(self) -> AstNode:
        node: AstNode = self._parse_atom()
        while self.current.type == TokenType.AS:
            self.next_token()
            cast_type: str = self.current.value
            self.expect(TokenType.IDENTIFIER)
            node = AsNode(node, cast_type)
        return node

    def _parse_atom(self) -> AstNode:
        match self.current.type:
            case TokenType.IDENTIFIER:
                return self._parse_identifier_or_call()
            case TokenType.INTEGER:
                return self._parse_int_literal()
            case TokenType.FLOAT:
                return self._parse_float_literal()
            case TokenType.STRING:
                return self._parse_string_literal()
            case TokenType.TRUE:
                self.next_token()
                return BooleanNode(True)
            case TokenType.FALSE:
                self.next_token()
                return BooleanNode(False)
            case TokenType.NULL:
                self.next_token()
                return NullNode()
            case TokenType.LPAREN:
                self.next_token()
                node: AstNode = self.parse_additive()
                self.expect(TokenType.RPAREN)
                return node
            case _:
                raise CornError(f"Unexpected token: {self.current.type}")

    def _parse_identifier_or_call(self) -> AstNode:
        module_name: Optional[str] = None
        if self.lookahead.type == TokenType.DOT:
            module_name = self.current.value
            self.next_token()
            self.expect(TokenType.DOT)
        name: str = self.current.value
        self.next_token()
        asserted: bool = False
        if self.current.type == TokenType.EXCLAMATION:
            asserted = True
            self.next_token()
        if self.current.type != TokenType.LPAREN:
            return VariableNode(module_name, name, asserted)
        self.next_token()
        args: list[AstNode] = []
        if self.current.type != TokenType.RPAREN:
            args.append(self.parse_additive())
            while self.current.type == TokenType.COMMA:
                self.next_token()
                args.append(self.parse_additive())
        self.expect(TokenType.RPAREN)
        return FunctionCallNode(module_name, name, args, asserted)

    def _parse_int_literal(self) -> NumberNode:
        value: int = int(self.current.value)
        self.next_token()
        return NumberNode(value)

    def _parse_float_literal(self) -> NumberNode:
        value: float = float(self.current.value)
        self.next_token()
        return NumberNode(value)

    def _parse_string_literal(self) -> StringNode:
        value: str = str(self.current.value)
        self.next_token()
        return StringNode(value)

    def parse_condition(self) -> AstNode:
        left: AstNode = self.parse_additive()
        COMPARE_OPS: tuple[TokenType, ...] = (
            TokenType.GE, TokenType.GT, TokenType.LE, TokenType.LT,
            TokenType.NE, TokenType.EQEQ, TokenType.IS,
        )
        if self.current.type not in COMPARE_OPS:
            return left
        op: TokenType = self.current.type
        self.next_token()
        if op == TokenType.IS:
            pass
        else:
            right = self.parse_additive()
            left = ExpressionNode(left, right, op)
        return left

    def parse_statement(self) -> AstNode:
        match self.current.type:
            case TokenType.RETURN:
                return self._parse_return()
            case TokenType.IF:
                return self._parse_if()
            case TokenType.WHILE:
                return self._parse_while()
            case TokenType.LOOP:
                return self._parse_loop()
            case TokenType.BREAK:
                self.next_token()
                return BreakNode()
            case TokenType.CONTINUE:
                self.next_token()
                return ContinueNode()
            case _:
                raise CornError(f"Unexpected token at line {self.current.line} col {self.current.col}")

    def _parse_return(self) -> ReturnNode:
        self.next_token()
        expr: Optional[AstNode] = None
        EXPR_STARTERS: tuple[TokenType, ...] = (
            TokenType.IDENTIFIER, TokenType.NULL, TokenType.INTEGER,
            TokenType.FLOAT, TokenType.STRING, TokenType.LPAREN,
        )
        if self.current.type in EXPR_STARTERS:
            expr = self.parse_additive()
        return ReturnNode(expr)

    def _parse_if(self) -> IfNode:
        self.next_token()
        self.expect(TokenType.LPAREN)
        condition: AstNode = self.parse_condition()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.LBRACE)
        then: BlockNode = self.parse_block()
        otherwise: Optional[BlockNode] = None
        if self.current.type == TokenType.ELSE:
            self.next_token()
            if self.current.type == TokenType.IF:
                otherwise = BlockNode([self.parse_statement()])
            else:
                self.expect(TokenType.LBRACE)
                otherwise = self.parse_block()
        return IfNode(condition, then, otherwise)

    def _parse_while(self) -> WhileNode:
        self.next_token()
        self.expect(TokenType.LPAREN)
        condition: AstNode = self.parse_condition()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.LBRACE)
        body: BlockNode = self.parse_block()
        return WhileNode(condition, body)

    def _parse_loop(self) -> WhileNode:
        self.next_token()
        self.expect(TokenType.LBRACE)
        body: BlockNode = self.parse_block()
        return WhileNode(BooleanNode(True), body)

    def parse_definition(self, is_safe: bool = False) -> AstNode:
        type_name: str = self.current.value
        is_nullable: bool = False
        self.next_token()
        if self.current.type == TokenType.QUESTION:
            is_nullable = True
            self.next_token()
        self.expect(TokenType.COLON)
        if self.current.type != TokenType.IDENTIFIER:
            raise CornError(f"Expected name after ':' at line {self.current.line} col {self.current.col}")
        name: str = self.current.value
        self.next_token()
        match self.current.type:
            case TokenType.LPAREN:
                return self._parse_function_def(type_name, name, is_safe=is_safe, is_nullable=is_nullable)
            case TokenType.EQ:
                return self._parse_typed_binding(type_name, [name], is_mut=False, is_nullable=is_nullable)
            case TokenType.COMMA:
                names: list[str] = self._parse_name_list(name)
                return self._parse_typed_binding(type_name, names, is_mut=False, is_nullable=is_nullable)
            case _:
                raise CornError(f"Expected '(' or '=' after name at line {self.current.line} col {self.current.col}")

    def parse_safe_def(self) -> AstNode:
        self.next_token()
        return self.parse_definition(is_safe=True)

    def _parse_function_def(self, return_type: str, name: str, is_safe: bool = False,
                            is_nullable: bool = False) -> FunctionDefNode:
        args: list[DefArgumentNode] = self._parse_function_args()
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.LBRACE)
        body: BlockNode = self.parse_block()
        return FunctionDefNode(return_type, name, args, body, False, is_safe=is_safe, is_nullable=is_nullable)

    def _parse_function_args(self) -> list[DefArgumentNode]:
        self.expect(TokenType.LPAREN)
        args: list[DefArgumentNode] = []
        while self.current.type != TokenType.RPAREN:
            if self.current.type != TokenType.IDENTIFIER:
                raise CornError(f"Expected type name in argument at line {self.current.line} col {self.current.col}")
            arg_type: str = self.current.value
            self.next_token()
            self.expect(TokenType.COLON)
            if self.current.type != TokenType.IDENTIFIER:
                raise CornError(f"Expected argument name at line {self.current.line} col {self.current.col}")
            arg_name: str = self.current.value
            self.next_token()
            args.append(DefArgumentNode(arg_type, arg_name))
            if self.current.type == TokenType.COMMA:
                self.next_token()
            elif self.current.type != TokenType.RPAREN:
                raise CornError(
                    f"Expected ',' or ')' in argument list at line {self.current.line} col {self.current.col}")
        return args

    def parse_mut(self) -> BindingNode:
        self.next_token()
        data: str = self.current.value
        if self.lookahead.type in (TokenType.EQ, TokenType.COMMA):
            return self._parse_dynamic_binding(data, is_mut=True)
        type_name: str = data
        is_nullable: bool = False
        self.next_token()
        if self.current.type == TokenType.QUESTION:
            is_nullable = True
            self.next_token()
        self.expect(TokenType.COLON)
        if self.current.type != TokenType.IDENTIFIER:
            raise CornError(f"Expected name after ':' at line {self.current.line} col {self.current.col}")
        names: list[str] = self._parse_name_list(self.current.value)
        return self._parse_typed_binding(type_name, names, is_mut=True, is_nullable=is_nullable)

    def parse_native_def(self) -> FunctionDefNode:
        self.next_token()
        return_type: str = self.current.value
        self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.COLON)
        if self.current.type != TokenType.IDENTIFIER:
            raise CornError("Expected native function name after ':'")
        fn_name: str = self.current.value
        self.next_token()
        args: list[NativeArgumentNode]
        var_args: bool
        args, var_args = self._parse_native_args()
        self.expect(TokenType.RPAREN)
        return FunctionDefNode(return_type, fn_name, args, None, True, var_args)

    def _parse_native_args(self) -> tuple[list[NativeArgumentNode], bool]:
        self.expect(TokenType.LPAREN)
        args: list[NativeArgumentNode] = []
        var_args: bool = False
        while self.current.type != TokenType.RPAREN:
            if self.current.type == TokenType.VARARGS:
                self.next_token()
                var_args = True
                if self.current.type != TokenType.RPAREN:
                    raise CornError("... must be followed by ')'")
                break
            if self.current.type != TokenType.IDENTIFIER:
                raise CornError(f"Expected type name in argument at line {self.current.line} col {self.current.col}")
            args.append(NativeArgumentNode(self.current.value))
            self.next_token()
            if self.current.type == TokenType.COMMA:
                self.next_token()
            elif self.current.type != TokenType.RPAREN:
                raise CornError(
                    f"Expected ',', '...' or ')' in argument list at line {self.current.line} col {self.current.col}")
        return args, var_args

    def _parse_dynamic_binding(self, name: Optional[str] = None, is_mut: bool = False) -> BindingNode:
        if not name:
            name = self.current.value
        names: list[str] = [name]
        self.next_token()
        while self.current.type == TokenType.COMMA:
            self.next_token()
            names.append(self.current.value)
            self.next_token()
        return self._parse_typed_binding(type_name=None, names=names, is_mut=is_mut, is_nullable=False)

    def _parse_typed_binding(self, type_name: Optional[str], names: list[str], is_mut: bool,
                             is_nullable: bool) -> BindingNode:
        self.expect(TokenType.EQ)
        exprs: list[AstNode] = [self.parse_additive()]
        while self.current.type == TokenType.COMMA:
            self.next_token()
            exprs.append(self.parse_additive())
        if len(exprs) == 1 and len(names) > 1:
            exprs = exprs * len(names)
        elif len(exprs) != len(names):
            raise CornError(f"Assignment count mismatch at line {self.current.line} col {self.current.col}")
        return BindingNode(names, [type_name] if type_name is not None else None, exprs, is_mut, is_nullable)

    def _parse_name_list(self, first: str) -> list[str]:
        names: list[str] = [first]
        self.next_token()
        while self.current.type == TokenType.COMMA:
            self.next_token()
            names.append(self.current.value)
            self.next_token()
        return names

    def parse_import(self) -> ImportNode:
        self.next_token()
        if self.current.type != TokenType.STRING:
            raise CornError(f"Expected module name in 'import' at line {self.current.line} col {self.current.col}")
        module_name: str = self.current.value
        self.next_token()
        return ImportNode(module_name)

    def parse_block(self) -> BlockNode:
        nodes: list[AstNode] = []
        while self.current.type not in (TokenType.RBRACE, TokenType.EOF):
            item: Optional[AstNode] = self._parse_block_item()
            if item is not None:
                nodes.append(item)
        if self.current.type == TokenType.RBRACE:
            self.next_token()
        return BlockNode(nodes)

    def _parse_block_item(self) -> Optional[AstNode]:
        match self.current.type:
            case TokenType.UNSAFE:
                self.next_token()
                self.expect(TokenType.LBRACE)
                body: BlockNode = self.parse_block()
                return UnsafeNode(body)
            case TokenType.IMPORT:
                return self.parse_import()
            case TokenType.IDENTIFIER:
                return self._parse_identifier_block_item()
            case TokenType.MUT:
                return self.parse_mut()
            case TokenType.NATIVE:
                return self.parse_native_def()
            case TokenType.SAFE:
                return self.parse_safe_def()
            case TokenType.RBRACE:
                return None
            case TokenType.EOF:
                return None
            case _:
                return self.parse_statement()

    def _parse_identifier_block_item(self) -> AstNode:
        match self.lookahead.type:
            case TokenType.QUESTION | TokenType.COLON:
                return self.parse_definition()
            case TokenType.EQ | TokenType.COMMA:
                return self._parse_dynamic_binding(is_mut=False)
            case _:
                return self.parse_additive()

    def parse(self) -> list[AstNode]:
        nodes: list[AstNode] = []
        while self.current.type != TokenType.EOF:
            nodes.append(self.parse_block())
        return nodes
