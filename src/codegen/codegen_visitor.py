from llvmlite import ir, binding
from typing import Optional, Union

from ..ast.ast_nodes import (
    UnsafeNode, ImportNode, ExpressionNode, VariableNode,
    FunctionCallNode, BindingNode, NullNode, NumberNode, StringNode,
    BooleanNode, BlockNode, DefArgumentNode, NativeArgumentNode,
    ReturnNode, FunctionDefNode, IfNode, DoWhileNode, WhileNode,
    BreakNode, ContinueNode, AsNode,
)
from ..ast.ast_visitor import AstVisitor
from ..error import CornError
from ..lexer import TokenType


class CodegenVisitor(AstVisitor):
    def __init__(self, module: ir.Module):
        self.type_map: dict[str, ir.Type] = {
            'boolean': ir.IntType(1),
            'int': ir.IntType(32),
            'int32': ir.IntType(32),
            'int64': ir.IntType(64),
            'float': ir.FloatType(),
            'float32': ir.FloatType(),
            'float64': ir.DoubleType(),
            'void': ir.VoidType(),
            'char': ir.IntType(8),
            'string': ir.IntType(8).as_pointer(),
        }
        self.module: ir.Module = module
        self.module.triple = binding.get_default_triple()
        self.symbol_table: dict[str, tuple[ir.Value, ir.Type]] = {}
        self.builder: ir.IRBuilder = ir.IRBuilder()
        self.loop_stack: list[tuple[ir.Block, ir.Block]] = []

    def visit_unsafe_node(self, node: UnsafeNode) -> None:
        pass

    def visit_import_node(self, node: ImportNode) -> None:
        pass

    def visit_null_node(self, node: NullNode) -> tuple[ir.Constant, ir.PointerType]:
        return ir.Constant(ir.IntType(8).as_pointer(), None), ir.IntType(8).as_pointer()

    def visit_number_node(self, node: NumberNode) -> tuple[ir.Constant, ir.Type]:
        value: Union[int, float] = node.value
        match value:
            case float():
                number_type: ir.Type = self.type_map['float']
            case int():
                number_type = self.type_map['int']
        return ir.Constant(number_type, value), number_type

    def visit_string_node(self, node: StringNode) -> tuple[ir.Value, ir.PointerType]:
        value: bytearray = bytearray(node.value + '\0', 'utf-8')
        ir_type: ir.ArrayType = ir.ArrayType(ir.IntType(8), len(value))
        const: ir.Constant = ir.Constant(ir_type, value)
        ptr: ir.Value = self.builder.alloca(ir_type)
        self.builder.store(const, ptr)
        zero: ir.Constant = ir.Constant(ir.IntType(32), 0)
        ptr = self.builder.gep(ptr, [zero, zero])
        return ptr, self.type_map['string']

    def visit_boolean_node(self, node: BooleanNode) -> tuple[ir.Constant, ir.IntType]:
        bool_type: ir.IntType = self.type_map['boolean']
        return ir.Constant(bool_type, int(node.value)), bool_type

    def visit_variable_node(self, node: VariableNode) -> tuple[ir.Value, ir.Type]:
        ptr: ir.Value
        ty: ir.Type
        ptr, ty = self.symbol_table[node.name]
        return self.builder.load(ptr), ty

    def visit_binding_node(self, node: BindingNode) -> None:
        for i in range(len(node.names)):
            value: ir.Value
            ty: ir.Type
            value, ty = self.visit(node.exprs[i])
            if node.names[i] not in self.symbol_table:
                ptr: ir.Value = self.builder.alloca(ty)
                self.symbol_table[node.names[i]] = ptr, ty
            else:
                ptr, _ = self.symbol_table[node.names[i]]
            self.builder.store(value, ptr)

    def visit_function_call_node(self, node: FunctionCallNode) -> tuple[ir.Value, ir.Type]:
        call_args: list[ir.Value] = []
        for arg in node.args:
            value: ir.Value
            _ty: ir.Type
            value, _ty = self.visit(arg)
            call_args.append(value)
        func: ir.Function
        ty: ir.Type
        func, ty = self.symbol_table[node.name]
        ret: ir.Value = self.builder.call(func, call_args)
        return ret, ty

    def _emit_int_binary_op(self, left: ir.Value, right: ir.Value, op: TokenType) -> tuple[ir.Value, ir.Type]:
        CMP_OPS: dict[TokenType, str] = {
            TokenType.LT: '<', TokenType.LE: '<=',
            TokenType.GT: '>', TokenType.GE: '>=',
            TokenType.NE: '!=', TokenType.EQEQ: '==',
        }
        if op in CMP_OPS:
            return self.builder.icmp_signed(CMP_OPS[op], left, right), ir.IntType(1)
        match op:
            case TokenType.PLUS:
                return self.builder.add(left, right), ir.IntType(32)
            case TokenType.MINUS:
                return self.builder.sub(left, right), ir.IntType(32)
            case TokenType.TIMES:
                return self.builder.mul(left, right), ir.IntType(32)
            case TokenType.DIVIDE:
                return self.builder.sdiv(left, right), ir.IntType(32)
            case TokenType.MOD:
                return self.builder.srem(left, right), ir.IntType(32)
            case TokenType.TILDE:
                val: ir.Value = self.builder.sdiv(left, right)
                return self.builder.fptosi(val, self.type_map['int']), ir.IntType(32)
            case TokenType.AND:
                return self.builder.and_(left, right), ir.IntType(32)
            case TokenType.OR:
                return self.builder.or_(left, right), ir.IntType(32)
            case TokenType.XOR:
                return self.builder.xor(left, right), ir.IntType(32)
            case TokenType.RSHIFT:
                return self.builder.ashr(left, right), ir.IntType(32)
            case TokenType.LSHIFT:
                return self.builder.shl(left, right), ir.IntType(32)
        raise CornError(f"Unknown integer binary operator: {op}")

    def _emit_float_binary_op(self, left: ir.Value, right: ir.Value, op: TokenType) -> tuple[ir.Value, ir.Type]:
        CMP_OPS: dict[TokenType, str] = {
            TokenType.LT: '<', TokenType.LE: '<=',
            TokenType.GT: '>', TokenType.GE: '>=',
            TokenType.NE: '!=', TokenType.EQEQ: '==',
        }
        if op in CMP_OPS:
            return self.builder.fcmp_ordered(CMP_OPS[op], left, right), ir.IntType(1)
        match op:
            case TokenType.PLUS:
                return self.builder.fadd(left, right), ir.FloatType()
            case TokenType.MINUS:
                return self.builder.fsub(left, right), ir.FloatType()
            case TokenType.TIMES:
                return self.builder.fmul(left, right), ir.FloatType()
            case TokenType.DIVIDE:
                return self.builder.fdiv(left, right), ir.FloatType()
            case TokenType.MOD:
                return self.builder.frem(left, right), ir.FloatType()
            case TokenType.TILDE:
                val: ir.Value = self.builder.fdiv(left, right)
                return self.builder.fptosi(val, self.type_map['int']), ir.IntType(32)
        raise CornError(f"Unknown float binary operator: {op}")

    def visit_expression_node(self, node: ExpressionNode) -> tuple[ir.Value, ir.Type]:
        left: ir.Value
        left_type: ir.Type
        left, left_type = self.visit(node.left)
        right: ir.Value
        right_type: ir.Type
        right, right_type = self.visit(node.right)
        if isinstance(left_type, ir.FloatType) and isinstance(right_type, ir.FloatType):
            return self._emit_float_binary_op(left, right, node.op)
        if isinstance(left_type, ir.IntType) and isinstance(right_type, ir.IntType):
            return self._emit_int_binary_op(left, right, node.op)
        raise CornError(f"Cannot apply operator {node.op} to types {left_type} and {right_type}")

    def visit_block_node(self, node: BlockNode) -> None:
        for child in node.nodes:
            self.visit(child)
            if self.builder.block is not None and self.builder.block.is_terminated:
                break

    def _collect_arg_types(self, node: FunctionDefNode) -> list[ir.Type]:
        return [self.type_map[arg.type_name] for arg in node.args if isinstance(arg, DefArgumentNode)]

    def _emit_function_args(self, func: ir.Function, args_name: list[str], args_type: list[ir.Type]) -> None:
        params_ptr: list[ir.Value] = []
        for i, typ in enumerate(args_type):
            ptr: ir.Value = self.builder.alloca(typ)
            self.builder.store(func.args[i], ptr)
            params_ptr.append(ptr)
        for i, name in enumerate(args_name):
            self.symbol_table[name] = params_ptr[i], args_type[i]

    def _emit_function_body(self, func: ir.Function, node: FunctionDefNode, return_type: ir.Type) -> None:
        entry: ir.Block = func.append_basic_block(f'{node.name}_entry')
        self.builder = ir.IRBuilder(entry)
        args_name: list[str] = []
        args_type: list[ir.Type] = []
        for arg in node.args:
            name: str
            typ: ir.Type
            assert isinstance(arg, DefArgumentNode)
            name, typ = self.visit_def_argument_node(arg)
            args_name.append(name)
            args_type.append(typ)
        self._emit_function_args(func, args_name, args_type)
        self.symbol_table[node.name] = func, return_type
        if node.body is not None:
            self.visit(node.body)
        if not self.builder.block.is_terminated:
            if return_type == ir.VoidType():
                self.builder.ret_void()
            else:
                self.builder.unreachable()

    def visit_function_def_node(self, node: FunctionDefNode) -> None:
        return_type: ir.Type = self.type_map[node.type_name]
        is_native: bool = node.native
        args_type: list[ir.Type] = self._collect_arg_types(node)
        fnty: ir.FunctionType = ir.FunctionType(return_type, args_type, var_arg=node.is_variadic)
        func: ir.Function = ir.Function(self.module, fnty, name=node.name)
        previous_builder: ir.IRBuilder = self.builder
        previous_variables: dict[str, tuple[ir.Value, ir.Type]] = self.symbol_table.copy()
        previous_loop_stack: list[tuple[ir.Block, ir.Block]] = self.loop_stack
        self.loop_stack = []
        if not is_native:
            self._emit_function_body(func, node, return_type)
        self.symbol_table = previous_variables
        self.symbol_table[node.name] = func, return_type
        self.builder = previous_builder
        self.loop_stack = previous_loop_stack

    def visit_def_argument_node(self, node: DefArgumentNode) -> tuple[str, ir.Type]:
        return node.name, self.type_map[node.type_name]

    def visit_native_argument_node(self, node: NativeArgumentNode) -> ir.Type:
        return self.type_map[node.type_name]

    def visit_return_node(self, node: ReturnNode) -> None:
        if not node.expr:
            self.builder.ret_void()
            return
        value: ir.Value
        _ty: ir.Type
        value, _ty = self.visit(node.expr)
        self.builder.ret(value)

    def visit_if_node(self, node: IfNode) -> None:
        condition: ir.Value
        _ty: ir.Type
        condition, _ty = self.visit(node.condition)
        then_block: ir.Block = self.builder.append_basic_block('if_then')
        merge_block: ir.Block = self.builder.append_basic_block('if_merge')
        else_block: ir.Block = self.builder.append_basic_block('if_else') if node.otherwise is not None else merge_block
        self.builder.cbranch(condition, then_block, else_block)
        self.builder.position_at_start(then_block)
        self.visit(node.then)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)
        if node.otherwise is not None:
            self.builder.position_at_start(else_block)
            self.visit(node.otherwise)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)
        self.builder.position_at_start(merge_block)

    def visit_do_while_node(self, node: DoWhileNode) -> None:
        body_block: ir.Block = self.builder.append_basic_block("do_while_body")
        cond_block: ir.Block = self.builder.append_basic_block("do_while_cond")
        exit_block: ir.Block = self.builder.append_basic_block("do_while_exit")
        self.builder.branch(body_block)
        self.builder.position_at_start(body_block)
        self.loop_stack.append((cond_block, exit_block))
        try:
            self.visit(node.body)
        finally:
            self.loop_stack.pop()
        self.builder.branch(cond_block)
        self.builder.position_at_start(cond_block)
        condition: ir.Value
        _ty: ir.Type
        condition, _ty = self.visit(node.condition)
        self.builder.cbranch(condition, body_block, exit_block)
        self.builder.position_at_start(exit_block)

    def visit_while_node(self, node: WhileNode) -> None:
        cond_block: ir.Block = self.builder.append_basic_block("while_cond")
        body_block: ir.Block = self.builder.append_basic_block("while_body")
        exit_block: ir.Block = self.builder.append_basic_block("while_exit")
        self.builder.branch(cond_block)
        self.builder.position_at_start(cond_block)
        condition: ir.Value
        _ty: ir.Type
        condition, _ty = self.visit(node.condition)
        self.builder.cbranch(condition, body_block, exit_block)
        self.builder.position_at_start(body_block)
        self.loop_stack.append((cond_block, exit_block))
        try:
            self.visit(node.body)
        finally:
            self.loop_stack.pop()
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        self.builder.position_at_start(exit_block)

    def visit_break_node(self, node: BreakNode) -> None:
        if not self.loop_stack:
            raise CornError("'break' used outside of a loop")
        _cond: ir.Block
        break_target: ir.Block
        _cond, break_target = self.loop_stack[-1]
        self.builder.branch(break_target)

    def visit_continue_node(self, node: ContinueNode) -> None:
        if not self.loop_stack:
            raise CornError("'continue' used outside of a loop")
        continue_target: ir.Block
        _exit: ir.Block
        continue_target, _exit = self.loop_stack[-1]
        self.builder.branch(continue_target)

    def _cast_int_to_int(self, val: ir.Value, src: ir.IntType, dst: ir.IntType) -> ir.Value:
        if dst.width > src.width:
            return self.builder.sext(val, dst)
        if dst.width < src.width:
            return self.builder.trunc(val, dst)
        return val

    def _cast_float_to_float(self, val: ir.Value, src: ir.Type, dst: ir.Type) -> ir.Value:
        if isinstance(dst, ir.DoubleType) and isinstance(src, ir.FloatType):
            return self.builder.fpext(val, dst)
        if isinstance(dst, ir.FloatType) and isinstance(src, ir.DoubleType):
            return self.builder.fptrunc(val, dst)
        return val

    def _cast_numeric(self, val: ir.Value, src: ir.Type, dst: ir.Type) -> Optional[ir.Value]:
        if isinstance(src, ir.IntType) and isinstance(dst, (ir.FloatType, ir.DoubleType)):
            return self.builder.sitofp(val, dst)
        if isinstance(src, (ir.FloatType, ir.DoubleType)) and isinstance(dst, ir.IntType):
            return self.builder.fptosi(val, dst)
        return None

    def _cast_pointer(self, val: ir.Value, src: ir.Type, dst: ir.Type) -> Optional[ir.Value]:
        if isinstance(src, ir.PointerType) and isinstance(dst, ir.PointerType):
            return self.builder.bitcast(val, dst)
        if isinstance(src, ir.PointerType) and isinstance(dst, ir.IntType):
            return self.builder.ptrtoint(val, dst)
        if isinstance(src, ir.IntType) and isinstance(dst, ir.PointerType):
            return self.builder.inttoptr(val, dst)
        return None

    def visit_as_node(self, node: AsNode) -> tuple[ir.Value, ir.Type]:
        expr_val: ir.Value
        expr_type: ir.Type
        expr_val, expr_type = self.visit(node.expr)
        target_type: ir.Type = self.type_map[node.cast_type]
        if isinstance(expr_type, ir.IntType) and isinstance(target_type, ir.IntType):
            return self._cast_int_to_int(expr_val, expr_type, target_type), target_type
        if isinstance(expr_type, (ir.FloatType, ir.DoubleType)) and isinstance(target_type,
                                                                               (ir.FloatType, ir.DoubleType)):
            return self._cast_float_to_float(expr_val, expr_type, target_type), target_type
        result: Optional[ir.Value] = self._cast_numeric(expr_val, expr_type, target_type)
        if result is not None:
            return result, target_type
        result = self._cast_pointer(expr_val, expr_type, target_type)
        if result is not None:
            return result, target_type
        raise CornError(f"Cannot cast from {expr_type} to {target_type}")
