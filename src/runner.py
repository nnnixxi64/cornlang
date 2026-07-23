from llvmlite import ir
from typing import TextIO

from .ast.ast_nodes import AstNode
from .codegen import CodeGenerator
from .jit import JitEngine
from .parser import Parser
from .semantic import SemanticAnalyzer


class Runner:
    def __init__(self, file: TextIO, debug: bool = False, emit_llvm: bool = False):
        self.file: TextIO = file
        self.is_debug: bool = debug
        self.emit_llvm: bool = emit_llvm

    def run(self) -> int:
        parser: Parser = Parser(self.file)
        ast: list[AstNode] = parser.parse()
        semantic: SemanticAnalyzer = SemanticAnalyzer(ast)
        ast = semantic.analyze()
        codegen: CodeGenerator = CodeGenerator(ast)
        ir_module: ir.Module = codegen.generate()
        if self.emit_llvm:
            print(ir_module)
        jit_engine: JitEngine = JitEngine(ir_module, self.is_debug)
        return jit_engine.run()
