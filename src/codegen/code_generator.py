from llvmlite import ir

from .codegen_visitor import CodegenVisitor
from ..ast.ast_nodes import AstNode

class CodeGenerator:
    def __init__(self, ast: list[AstNode]):
        self.ast: list[AstNode] = ast
        self.module: ir.Module = ir.Module('main')
        self.visitor: CodegenVisitor = CodegenVisitor(self.module)

    def generate(self) -> ir.Module:
        for node in self.ast:
            self.visitor.visit(node)
        return self.module
