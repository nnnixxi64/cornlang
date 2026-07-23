import sys

from src import Runner


def main() -> None:
    args: list[str] = sys.argv[1:]
    if not args:
        print('Usage: python3 cornc.py <filename>')
        raise TypeError('Expected a <file>')
    filename: str = sys.argv[1]
    is_debug: bool = '--debug' in sys.argv or '-d' in sys.argv
    emit_llvm: bool = '--emit-llvm' in sys.argv
    with open(filename) as file:
        runner: Runner = Runner(file, is_debug, emit_llvm)
        exit_code: int = runner.run()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
