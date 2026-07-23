from ctypes import CFUNCTYPE, c_int
from llvmlite import ir, binding


class JitEngine:
    def __init__(self, module: ir.Module, debug: bool = False):
        self.module: ir.Module = module
        self.is_debug: bool = debug

    def run(self) -> int:
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()
        ir_parsed: binding.ModuleRef = binding.parse_assembly(str(self.module))
        if self.is_debug:
            ir_parsed.verify()
        target_machine: binding.TargetMachineRef = binding.Target.from_default_triple().create_target_machine()
        engine: binding.ExecutionEngineRef = binding.create_mcjit_compiler(ir_parsed, target_machine)
        engine.finalize_object()
        entry: int = engine.get_function_address('main')
        cfunc = CFUNCTYPE(c_int)(entry)
        return int(cfunc())
