from ast import *
import enum
import json
import autogolf
from os.path import join, dirname
import multiprocessing
import os
import zlib


jsonfile_cache = {}

class TestCodeStatus(enum.Enum):
    SUCCESS = 0
    TC_FAIL = 1
    ERROR = 2
    ERROR_UNRECOVERABLE = 3
    TIMEOUT = 4

SKIP_FIELD_NODES_COMBOS = {
    ("type_ignores", Module),
    ("lineno", Assign)
}


# noinspection PyBroadException
def test_code(task_num, code, return_on_first_fail=True) -> TestCodeStatus:
    if task_num not in jsonfile_cache:
        jsonfile = join(dirname(dirname(__file__)), "infos", f"task{task_num:03d}.json")
        with open(jsonfile, 'r') as f:
            data = json.load(f)
            tcs = {}
            i=0
            for tcdata in data["train"] + data["test"] + data["arc-gen"]:
                i += 1
                tcs[i] = tcdata
            jsonfile_cache[task_num] = tcs

    import importlib.util
    spec = importlib.util.spec_from_loader('epic_facility', loader=None)
    module = importlib.util.module_from_spec(spec)
    try:
        exec(code, module.__dict__)
    except (SyntaxError, TypeError, NameError, ModuleNotFoundError, AttributeError, IndexError):
        return TestCodeStatus.ERROR_UNRECOVERABLE
    if not hasattr(module, "p"):
        return TestCodeStatus.ERROR_UNRECOVERABLE
    program = getattr(module, "p")
    if not callable(program):
        return TestCodeStatus.ERROR_UNRECOVERABLE

    failed = False
    for tcnum in jsonfile_cache[task_num]:
        tc_data = jsonfile_cache[task_num][tcnum]
        inp = tc_data["input"]
        out = tc_data["output"]
        try:
            res = program(inp)
        except:
            return TestCodeStatus.ERROR
        try:
            res = json.loads(json.dumps(res).replace("true", "1").replace("false", "0"))
        except (TypeError, ValueError):
            return TestCodeStatus.ERROR_UNRECOVERABLE
        if res != out:
            failed = True
            if return_on_first_fail:

                return TestCodeStatus.TC_FAIL
    if failed:
        return TestCodeStatus.TC_FAIL
    return TestCodeStatus.SUCCESS


def nuke_char_gen(code, exclude_indicies: list[int] = None, exclude_chars: str = None):
    # O(n)
    if exclude_indicies is None:
        exclude_indicies = []
    if exclude_chars is None:
        exclude_chars = ""
    for i, c in enumerate(code):
        if c in exclude_chars:
            continue
        if i in exclude_indicies:
            continue
        yield code[:i] + code[i+1:]


def nuke_range_char_gen(code):
    # O(n**2)
    for a in range(len(code)):
        for b in range(a+1,len(code)):
            yield code[:a] + code[b:]


def sub_char_gen(code, charset=None, exclude_indicies: list[int] = None, exclude_chars: str = None):
    # O(m*n)
    if exclude_indicies is None:
        exclude_indicies = []
    if exclude_chars is None:
        exclude_chars = ""
    if charset is None:
        charset = "".join({*code,*"0123456789*+^><~-.,'\"|&"})
    for i, c in enumerate(code):
        if c in exclude_chars:
            continue
        if i in exclude_indicies:
            continue
        for sub_char in charset:
            yield code[:i] + sub_char + code[i+1:]


# todo swap char gen which is O(n**2)
# todo nuke range char gen which is O(n**2)


# tried so far (10/12/2025):
# nuke 1x
# nuke 2x
# nuke 1x sub 1x
# nuke range


TIMEOUT = 4.0


# modify this function to do stuff
def charbrute(task_num, code):
    import warnings
    warnings.filterwarnings("ignore")

    for final in nuke_range_char_gen(code):
        if test_code(task_num, final) == TestCodeStatus.SUCCESS:
            print(f"new best on t{task_num} ({len(code)} -> {len(final)}): {final}")


def main():
    import warnings
    warnings.filterwarnings("ignore")

    TEST_EXPORT_DIR_PATH = r"C:\Users\quasar\Downloads\export-1760312562"
    while not os.path.isdir(TEST_EXPORT_DIR_PATH):
        print("Export dir path not found. Enter > ", end="")
        TEST_EXPORT_DIR_PATH = input()
    DO_COMPRESSED_SOLS = False
    DO_GX2_SOLS = False

    task_paths = [join(TEST_EXPORT_DIR_PATH, fname) for fname in os.listdir(TEST_EXPORT_DIR_PATH)]

    task_contents = {}
    task_compressed = {}
    for task_path in task_paths:
        n = int(os.path.basename(task_path).removesuffix('.py').removeprefix('task'), 10)
        with open(task_path, 'rb') as f:
            data = f.read()
            if len(data) == 0:
                continue
            if b'g*2' in data and not DO_GX2_SOLS:
                continue
            if data.startswith(b"#coding:l1"):  # i just cant deal with this rn
                new = data.decode('l1').removeprefix('#coding:l1\nimport zlib\nexec(zlib.decompress(bytes(')
                new = new.removesuffix(",'l1'),-9))")
                new = new[1:-1]
                # scuffed asf !
                new = new.replace('\\\\', '\\\\')
                new = new.replace("\\0", '\x00')
                new = new.replace("\\n", '\x0a')
                new = new.replace("\\r", '\x0d')
                new = new.replace("\\'", "'")
                new = new.replace('\\"', '"')
                decompressed = zlib.decompress(new.encode('l1'), -9)
                try:
                    parse(decompressed)
                    task_contents[n] = decompressed
                    task_compressed[n] = True
                except (SyntaxError, TypeError, ValueError, IndentationError) as e:
                    print(f"Failed to parse task {n}. Skipping")
                continue
            try:
                parse(data)
                task_contents[n] = data
                task_compressed[n] = False
            except (SyntaxError, TypeError, ValueError, IndentationError):
                print(f"Failed to parse task {n}. Skipping")
    print("All sols loaded.")

    task_filtered = {tn: task_contents[tn] for tn in task_contents
                       if DO_COMPRESSED_SOLS or (not task_compressed[tn])}

    for task_num in task_filtered:
        code = autogolf.autogolf(task_contents[task_num].decode('l1'))

        print(f"v charbruting {task_num} ...")

        t = multiprocessing.Process(target=charbrute, args=(task_num, code))
        t.start()
        t.join(timeout=TIMEOUT)  # listening to the jeopardy theme song waiting for ts to finish rn
        t.terminate()  # send kill signal or something
        t.join()  # wait for it to die
        print(f"^ done charbruting {task_num}\n")


if __name__ == '__main__':
    main()
