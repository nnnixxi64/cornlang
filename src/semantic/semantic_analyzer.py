from .semantic_visitor import SemanticVisitor
from ..ast.ast_nodes import AstNode


class SemanticAnalyzer:
    def __init__(self, ast: list[AstNode]) -> None:
        self.ast: list[AstNode] = ast
        self.visitor: SemanticVisitor = SemanticVisitor()

    def analyze(self) -> list[AstNode]:
        nodes: list[AstNode] = []
        for node in self.ast:
            node = self.visitor.visit(node)
            nodes.append(node)
        return nodes
