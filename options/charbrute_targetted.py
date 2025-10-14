import ast
import enum
import json
import autogolf
from time import time, sleep
from os.path import join, dirname
import multiprocessing
import memory_limit
import os


"""
charbrute but you control what is going on and it searches the whole range
"""


jsonfile_cache = {}

class TestCodeStatus(enum.Enum):
    SUCCESS = 0
    TC_FAIL = 1
    ERROR = 2
    ERROR_UNRECOVERABLE = 3
    TIMEOUT = 4


# noinspection PyBroadException
def test_code(task_num, code, return_on_first_fail=True) -> TestCodeStatus:
    try:
        memory_limit.assign_job(memory_limit.create_job())
        memory_limit.limit_memory(100 * 1024 * 1024)
    except Exception as e:  # ur not on windows buddy
        pass
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
    except Exception:
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
        except Exception:
            return TestCodeStatus.ERROR_UNRECOVERABLE
        if res != out:
            failed = True
            if return_on_first_fail:

                return TestCodeStatus.TC_FAIL
    if failed:
        return TestCodeStatus.TC_FAIL
    return TestCodeStatus.SUCCESS


def test_code_with_alert(task_num, code, score_to_beat):
    if len(code) < score_to_beat and test_code(task_num, code) == TestCodeStatus.SUCCESS:
        msg = f"new best on t{task_num:03d} ({score_to_beat} -> {len(code)}): {code}"
        print(msg)
        with open("brute.txt", 'a') as f:
            print(msg, file=f)


def test_code_with_alert_batched(task_num, codes, score_to_beat):
    for code in codes:
        test_code_with_alert(task_num, code, score_to_beat)



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
    minimum = 0
    if "p=lambda g" in code:
        minimum = len("p=lambda g")
    if "def p(g):" in code:
        minimum = len("def p(g):")
    for a in range(minimum, len(code)):
        for b in range(a+1,len(code)):
            yield code[:a] + code[b:]


def sub_char_gen(code, charset=None, exclude_indicies: list[int] = None, exclude_chars: str = None):
    # O(m*n)
    if exclude_indicies is None:
        exclude_indicies = []
    if exclude_chars is None:
        exclude_chars = ""
    if charset is None:
        charset = "".join({*code,*"0123456789*+^><~-.,%/|&"})
    for i, c in enumerate(code):
        if c in exclude_chars:
            continue
        if i in exclude_indicies:
            continue
        for sub_char in charset:
            yield code[:i] + sub_char + code[i+1:]


# todo swap char gen which is O(n**2)


# tried so far (10/12/2025):
# nuke 1x
# nuke 2x
# nuke 1x sub 1x
# nuke range


# timeout per batch
TIMEOUT_PER_BATCH = 7.0
# number of code variations to run per batch
BATCH_SIZE = 5


# modify this function to do stuff
def charbrute_overall_gen(task_num, code, score_to_beat):
    for n1 in nuke_range_char_gen(code):
        for final in sub_char_gen(n1):
            yield final



def charbrute(task_num, code, score_to_beat=None):
    import warnings
    warnings.filterwarnings("ignore")

    score_to_beat = score_to_beat or len(code)
    max_processes = os.cpu_count() - 1 or 1  # todo
    pool = [None] * max_processes  # todo
    batch = []
    for final in charbrute_overall_gen(task_num, code, score_to_beat):
        if len(batch) < BATCH_SIZE:
            # sanity checks
            try:
                ast.parse(final)
            except:
                continue
            if ('p=lambda' not in final) and ('def p(' not in final):
                continue
            batch.append(final)
            continue

        # find place in pool for it
        i = -1
        while True:
            i = (i+1) % len(pool)
            if pool[i] is None:  # found a spot
                t = multiprocessing.Process(target=test_code_with_alert_batched, args=(task_num, batch, score_to_beat))
                t.start()
                pool[i] = (t, time())
                break
            else:  # kill overdue processes
                t, start_time = pool[i]
                if time() - start_time > TIMEOUT_PER_BATCH or not t.is_alive():  # DIE DIE DIE 🩸🩸🩸🩸 🔪🔪🔪
                    t.terminate()  # send kill signal or something
                    t.join()  # wait for it to die
                    pool[i] = None
                sleep(0.001)
        batch.clear()


def main():
    import warnings
    warnings.filterwarnings("ignore")

    # TEST_EXPORT_DIR_PATH = r"C:\Users\quasar\Downloads\export-1760311649"
    # while not os.path.isdir(TEST_EXPORT_DIR_PATH):
    #     print("Export dir path not found. Enter > ", end="")
    #     TEST_EXPORT_DIR_PATH = input()
    # DO_COMPRESSED_SOLS = False
    # DO_GX2_SOLS = True
    #
    # task_paths = [join(TEST_EXPORT_DIR_PATH, fname) for fname in os.listdir(TEST_EXPORT_DIR_PATH)]
    #
    # task_contents = {}
    # task_compressed = {}
    # for task_path in task_paths:
    #     n = int(os.path.basename(task_path).removesuffix('.py').removeprefix('task'), 10)
    #     with open(task_path, 'rb') as f:
    #         data = f.read()
    #         if len(data) == 0:
    #             continue
    #         if b'g*2' in data and not DO_GX2_SOLS:
    #             continue
    #         if data.startswith(b"#coding:l1"):  # i just cant deal with this rn
    #             new = data.decode('l1').removeprefix('#coding:l1\nimport zlib\nexec(zlib.decompress(bytes(')
    #             new = new.removesuffix(",'l1'),-9))")
    #             new = new[1:-1]
    #             # scuffed asf !
    #             new = new.replace('\\\\', '\\\\')
    #             new = new.replace("\\0", '\x00')
    #             new = new.replace("\\n", '\x0a')
    #             new = new.replace("\\r", '\x0d')
    #             new = new.replace("\\'", "'")
    #             new = new.replace('\\"', '"')
    #             decompressed = zlib.decompress(new.encode('l1'), -9)
    #             try:
    #                 parse(decompressed)
    #                 task_contents[n] = decompressed
    #                 task_compressed[n] = True
    #             except (SyntaxError, TypeError, ValueError, IndentationError) as e:
    #                 print(f"Failed to parse task {n}. Skipping")
    #             continue
    #         try:
    #             parse(data)
    #             task_contents[n] = data
    #             task_compressed[n] = False
    #         except (SyntaxError, TypeError, ValueError, IndentationError):
    #             print(f"Failed to parse task {n}. Skipping")
    # print("All sols loaded.")
    #
    # task_filtered = {tn: task_contents[tn] for tn in task_contents
    #                    if DO_COMPRESSED_SOLS or (not task_compressed[tn])}

    WS_SERVER_WORKING_DIR = r"C:\Users\quasar\Downloads\7WPr\working"
    while not os.path.isdir(WS_SERVER_WORKING_DIR):
        print("Export dir path not found. Enter > ", end="")

    tasks_possible_sols = {}
    for taskfolder in os.listdir(WS_SERVER_WORKING_DIR):
        taskfolder_path = join(WS_SERVER_WORKING_DIR, taskfolder)
        taskjson_path = join(taskfolder_path, sorted(os.listdir(taskfolder_path))[-1])
        with open(taskjson_path, 'r') as f:
            data = json.load(f)
        task_num = int(taskfolder[4:], 10)
        tasks_possible_sols[task_num] = []
        for line in data['annotations'].splitlines(keepends=False):
            if ("p=lambda" in line or ("def p(" in line and "return" in line)) and "#" != line.strip()[0]:
                tasks_possible_sols[task_num].append(line)

    for task_num in tasks_possible_sols:
        if task_num != 5:
            continue
        print(f"v charbruting {task_num} ...")
        for i, code in [*enumerate(tasks_possible_sols[task_num])][-3:]:
            print(f"version {i+1}/{len(tasks_possible_sols[task_num])}")
            try:
                code = autogolf.autogolf(code)
            except Exception:
                continue

            charbrute(task_num, code, min(map(len,tasks_possible_sols[task_num])))
        print(f"^ done charbruting {task_num}\n")


if __name__ == '__main__':
    main()
