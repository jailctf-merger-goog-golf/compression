import sys
from sys import argv
from options import autogolf, compression
from json import dumps
from typing import Any


def print_usage_and_exit():
    print(f"""
Usage: python3 {argv[0]} <list|run|var_brute> [args...]

Example:
 - python3 {argv[0]} list
 - python3 {argv[0]} run autogolf
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
            output_bytes = autogolf.autogolf(input_bytes.decode('l1'))
            debug = f"Success ({len(input_bytes)} -> {len(output_bytes)})".encode()
        except AssertionError as e:
            output_bytes = input_bytes
            debug = str(e.args[0]).encode('l1')
        return output_bytes, debug


class CompressionV1FastOption(Option):
    def __init__(self, name: str):
        super().__init__(name)
        self.local_only = False

    def run(self, input_bytes: bytes) -> tuple[bytes, bytes]:
        compressed = compression.get_compressed(input_bytes, max_brute=3_000, use_tqdm=False)
        return compressed, b""


options = [
    AutogolfOption("autogolf-v1"),
    CompressionV1FastOption("compression-v1-fast")
]


def main():
    first_arg = argv[1]
    if first_arg == "list":
        print(dumps([option.json() for option in options]))
    elif first_arg == "run":

        if len(argv) < 3:
            print_usage_and_exit()

        second_arg = argv[2]

        inp = bytes.fromhex(input('hex input > '))

        for option in options:
            if option.name == second_arg:
                out, debug = option.run(inp)
                break
        else:
            print(f'no option named {repr(second_arg)}')
            exit(1)

        # run_type = argv[2]
        # if run_type == 'compression-v1':
        #     compressed = get_compressed(inp, max_brute=10_000, use_tqdm=False)
        # elif run_type == 'compression-v1-fast':
        #
        # else:
        #     raise ValueError(f"Unknown compression type of {run_type!r}")

        print(out)
        print(debug, file=sys.stderr)


if __name__ == "__main__":
    main()
