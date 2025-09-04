import sys
from sys import argv
from options import autogolf, compression, infgen_analysis
from json import dumps
from typing import Any


def print_usage_and_exit():
    print(f"""
Usage: python3 {argv[0]} <list|run|var_brute> [args...]

Example:
 - python3 {argv[0]} list
 - python3 {argv[0]} run autogolf
 - python3 {argv[0]} run-from-file /path/to/file.py autogolf
    """.strip())
    exit(1)


if len(argv) == 1:
    print_usage_and_exit()


class Option:
    def __init__(self, name: str, local_only=True):
        self.name = name
        self.local_only = local_only  # to avoid nuking remote cpu
        # todo handle arguments
        self.args: list[str] = []

    def run(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        """should return a tuple of (output, debug)"""
        pass

    def json(self) -> Any:
        return {"name": self.name, "local_only": self.local_only}


class AutogolfOption(Option):
    def __init__(self, name: str):
        super().__init__(name)
        self.local_only = False

    def run(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        try:
            output_bytes = autogolf.autogolf(input_bytes.decode('l1')).encode('l1')
            if len(output_bytes) > len(input_bytes):
                debug = f"Failure ({len(input_bytes)}b -> {len(output_bytes)}b)"
                output_bytes = input_bytes
            else:
                debug = f"Success ({len(input_bytes)}b -> {len(output_bytes)}b)".encode()
        except AssertionError as e:
            output_bytes = input_bytes
            debug = str(e.args[0]).encode('l1')
        return output_bytes, debug


class CompressionV1FastOption(Option):
    def __init__(self, name: str):
        super().__init__(name)
        self.local_only = False

    def run(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        output_bytes = compression.get_compressed(input_bytes, max_brute=3_000, use_tqdm=False)
        if len(output_bytes) > len(input_bytes):
            msg = f"Compressed would not be smaller ({len(input_bytes)}b -> {len(output_bytes)}b). Left unchanged."
            return input_bytes, msg.encode()
        return output_bytes, f"Success ({len(input_bytes)}b -> {len(output_bytes)}b)!".encode()


class InfgenAnalysisOption(Option):
    def __init__(self, name: str):
        super().__init__(name)
        self.local_only = False

    def run(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        if not input_bytes.startswith(b"#coding:l1"):
            return input_bytes, b'Does not start with #coding:l1. Skipping'

        new = input_bytes.decode('l1').removeprefix('#coding:l1\nimport zlib\nexec(zlib.decompress(bytes(')
        new = new.removesuffix(",'l1'),-9))")
        new = new[1:-1]
        # scuffed asf !
        new = new.replace('\\\\', '\\\\')
        new = new.replace("\\0", '\x00')
        new = new.replace("\\n", '\x0a')
        new = new.replace("\\r", '\x0d')
        new = new.replace("\\'", "'")
        new = new.replace('\\"', '"')
        new = new.encode('l1')
        debug_bytes = infgen_analysis.infgen_call(new)
        return input_bytes, debug_bytes.encode('l1')


options = [
    AutogolfOption("autogolf-v1"),
    CompressionV1FastOption("compression-v1-fast"),
    InfgenAnalysisOption("infgen-analysis")
]


def main():
    first_arg = argv[1]

    if first_arg == "list":
        print(dumps([option.json() for option in options]))
    elif first_arg == "run" or first_arg == "run-from-file":

        if len(argv) < 3:
            print_usage_and_exit()

        if first_arg == "run-from-file":
            try:
                with open(argv.pop(2), 'rb') as f:
                    inp = f.read()
            except FileNotFoundError as e:
                print(e)
                print("no file found")
                exit(1)
        else:
            inp = bytes.fromhex(input('hex input > '))

        second_arg = argv[2]

        for option in options:
            if option.name == second_arg:
                out, debug = option.run(inp)
                break
        else:
            print(f'no option named {repr(second_arg)}', file=sys.stderr)
            exit(1)

        print(out.hex())
        print(debug.decode('l1'), file=sys.stderr)


if __name__ == "__main__":
    main()
