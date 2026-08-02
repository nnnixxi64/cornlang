class Mangler:
    def __init__(self) -> None:
        self.typecode_map: dict[str, str] = {
            'boolean': 'b',
            'int8': 'c',
            'int16': 's',
            'int': 'i',
            'int32': 'i',
            'int64': 'l',
            'float': 'f',
            'float32': 'f',
            'float64': 'd',
            'void': 'v',
            'char': 'c',
            'string': 't',
        }

    def mangle_function_name(self, name: str, args: list[str], module_name: str = '') -> str:
        if name == 'main' and module_name == '':
            return name
        types_signature: str = ''
        for type_name in args:
            types_signature += self.typecode_map[type_name]
        if module_name:
            module_name = 'N' + str(len(module_name)) + module_name
        return '_Z' + module_name + str(len(name)) + name + types_signature

    def mangle_variable_name(self, name: str, module_name: str = '') -> str:
        if module_name:
            module_name = 'N' + str(len(module_name)) + module_name
        return '_Z' + module_name + str(len(name)) + name
