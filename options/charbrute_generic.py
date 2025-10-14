from ast import *
import enum
import json
import autogolf
from os.path import join, dirname
import multiprocessing, os, zlib, itertools, random, time


"""
charbrute but you just bash it with a hammer and hope it fixes it
"""


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
            res = json.loads(json.dumps(res))
        except (TypeError, ValueError):
            return TestCodeStatus.ERROR_UNRECOVERABLE
        if res != out:
            failed = True
            if return_on_first_fail:

                return TestCodeStatus.TC_FAIL
    if failed:
        return TestCodeStatus.TC_FAIL
    return TestCodeStatus.SUCCESS


def nuke_char_gen(code, exclude_indices: list[int] = [0, 1, 2, 3, 4, 5], exclude_chars: str = None):
    # O(n)
    if exclude_indices is None:
        exclude_indices = []
    if exclude_chars is None:
        exclude_chars = ""
    for i, c in enumerate(code):
        if c in exclude_chars:
            continue
        if i in exclude_indices:
            continue
        yield code[:i] + code[i+1:]


def nuke_k_char_gen(code, k, exclude_indices: list[int] = [0, 1, 2, 3, 4, 5], exclude_chars: str = None):
    exclude_indices_set = set(exclude_indices or [])
    exclude_chars_set = set(exclude_chars or "")

    valid_indices = [
        i for i, char in enumerate(code)
        if i not in exclude_indices_set and char not in exclude_chars_set
    ]

    k = min(k, len(valid_indices))

    for indices_to_delete in itertools.combinations(valid_indices, k):
        indices_to_delete_set = set(indices_to_delete)
        
        yield "".join(
            char for i, char in enumerate(code)
            if i not in indices_to_delete_set
        )


def nuke_range_char_gen(code):
    # O(n**2)
    for a in range(len(code)):
        for b in range(a+1,len(code)):
            yield code[:a] + code[b:]



def sub_char_gen(code, charset=None, exclude_indices: list[int] = [0, 1, 2, 3, 4, 5], exclude_chars: str = None):
    # O(m*n)
    if exclude_indices is None:
        exclude_indices = []
    if exclude_chars is None:
        exclude_chars = ""
    if charset is None:
        charset = "".join({*code,*"0123456789*+^><~-.,'\"|&"})
    for i, c in enumerate(code):
        if c in exclude_chars:
            continue
        if i in exclude_indices:
            continue
        for sub_char in charset:
            yield code[:i] + sub_char + code[i+1:]


def sub_k_char_gen(code, k, charset=None, exclude_indices: list[int] = [0, 1, 2, 3, 4, 5], exclude_chars: str = None):
    exclude_indices_set = set(exclude_indices or [])
    exclude_chars_set = set(exclude_chars or "")

    if charset is None:
        charset = "".join(sorted(set(code) | set("0123456789*+^><~-.,'\"|&")))

    valid_indices = [
        i for i, char in enumerate(code)
        if i not in exclude_indices_set and char not in exclude_chars_set
    ]

    k = min(k, len(valid_indices))

    for indices_to_change in itertools.combinations(valid_indices, k):
        for sub_chars in itertools.product(charset, repeat=k):
            temp_code = list(code)
            for index, new_char in zip(indices_to_change, sub_chars):
                temp_code[index] = new_char
            yield "".join(temp_code)

def mutate_code_gen(code: str, s_k: int = 0, d_k: int = 0, charset: str = None, exclude_indices: list[int] = [0, 1, 2, 3, 4, 5], exclude_chars: str = None):
    if not s_k and not d_k:
        return

    exclude_indices_set = set(exclude_indices or [])
    exclude_chars_set = set(exclude_chars or "")

    if charset is None:
        charset = "".join(sorted(set(code) | set("0123456789*+^><~-.,'\"|&")))

    valid_indices = [
        i for i, char in enumerate(code)
        if i not in exclude_indices_set and char not in exclude_chars_set
    ]

    if s_k + d_k > len(valid_indices):
        return

    random.shuffle(valid_indices)
    shuffled_charset = list(charset)
    random.shuffle(shuffled_charset)

    for affected_indices in itertools.combinations(valid_indices, s_k + d_k):
        for del_indices_tuple in itertools.combinations(affected_indices, d_k):
            del_indices_set = set(del_indices_tuple)
            sub_indices = [i for i in affected_indices if i not in del_indices_set]

            for sub_chars in itertools.product(shuffled_charset, repeat=s_k):
                sub_map = dict(zip(sub_indices, sub_chars))
                
                new_code = []
                for i, char in enumerate(code):
                    if i in del_indices_set:
                        continue  # Delete character
                    elif i in sub_map:
                        new_code.append(sub_map[i])  # Substitute character
                    else:
                        new_code.append(char)  # Keep original

                final_code = "".join(new_code)
                try:
                    parse(final_code)
                    yield final_code
                except:
                    continue

def move_chunk_gen(code: str, n: int = 10):
    code_len = len(code)

    starts = [*range(6, code_len)] # don't change things in the first 6 characters
    lengths = [*range(1, n + 1)]
    inserts = [*range(6, code_len)]

    random.shuffle(starts)
    random.shuffle(lengths)
    random.shuffle(inserts)

    for i in starts:
        for length in lengths:
            start = i
            end = i + length
            if end > code_len:
                continue

            chunk = code[start:end]

            remaining_code = code[:start] + code[end:]
            for insert_pos in inserts:
                if insert_pos > len(remaining_code):
                    continue
                
                yield remaining_code[:insert_pos] + chunk + remaining_code[insert_pos:]

def combined_mutation_gen(code: str, s_k: int = 1, d_k: int = 1, n: int = 10, charset: str = None, exclude_indices: list[int] = None):
    exclude_indices_set = set(exclude_indices if exclude_indices is not None else [0, 1, 2, 3, 4, 5])

    if charset is None:
        charset = "".join(set(code) | set("0123456789*+^><~-.,%/|&"))
    
    while True:
        valid_indices = [i for i, char in enumerate(code) if i not in exclude_indices_set]
        
        mutated_code = code
        if s_k + d_k > 0 and s_k + d_k <= len(valid_indices):
            s_k_temp = s_k
            d_k_temp = d_k
            if random.getrandbits(3) < 2:
                d_k_temp = random.randint(1, d_k - 1)
            if random.getrandbits(3) < 1:
                s_k_temp = random.randint(1, s_k - 1)
            affected_indices = random.sample(valid_indices, s_k_temp + d_k_temp)
            del_indices = random.sample(affected_indices, d_k_temp)
            
            sub_map = {}
            for index in affected_indices:
                if index not in del_indices:
                    sub_map[index] = random.choice(charset)

            new_code_list = []
            for i, char in enumerate(code):
                if i in del_indices:
                    continue
                elif i in sub_map:
                    if random.getrandbits(1) == 0: # do an insertion instead of a substitution sometimes
                        new_code_list.append(char)
                    new_code_list.append(sub_map[i])
                else:
                    new_code_list.append(char)
            
            mutated_code = "".join(new_code_list)

        final_code = mutated_code
        if len(final_code) >= len(code):
            continue

        if n:
            min_move_index = 0
            if exclude_indices_set:
                min_move_index = max(exclude_indices_set) + 1

            if len(mutated_code) > min_move_index:
                start = random.randint(min_move_index, len(mutated_code) - 1)
                length = random.randint(1, n)
                end = min(start + length, len(mutated_code))
                chunk = mutated_code[start:end]

                remaining_code = mutated_code[:start] + mutated_code[end:]
                insert_pos = random.randint(min_move_index, len(remaining_code))
                final_code = remaining_code[:insert_pos] + chunk + remaining_code[insert_pos:]
        


        try:
            parse(final_code)
            yield final_code
        except:
            continue

# todo swap char gen which is O(n**2)
# todo nuke range char gen which is O(n**2)


# tried so far (10/12/2025):
# nuke 1x
# nuke 2x
# nuke 1x sub 1x
# nuke range


TIMEOUT = 20.0


# modify this function to do stuff
def charbrute(task_num, code):
    import warnings
    warnings.filterwarnings("ignore")

    for final in combined_mutation_gen(code, 3, 2, 0):
        if test_code(task_num, final) == TestCodeStatus.SUCCESS:
            print(f"hit on t{task_num:03d} ({len(code)} -> {len(final)}): {final}" + "!"*100)
            with open('brute.txt', 'a') as f:
                f.write(f"new best on t{task_num:03d} ({len(code)} -> {len(final)}): {final}\n")


def main():
    import warnings
    warnings.filterwarnings("ignore")

    TEST_EXPORT_DIR_PATH = r"C:\Users\quasar\Downloads\export-1760312562"
    while not os.path.isdir(TEST_EXPORT_DIR_PATH):
        print("Export dir path not found. Enter > ", end="")
        TEST_EXPORT_DIR_PATH = input()
    DO_COMPRESSED_SOLS = False
    DO_GX2_SOLS = True
    duplicate = True

    task_paths = [join(TEST_EXPORT_DIR_PATH, fname) for fname in os.listdir(TEST_EXPORT_DIR_PATH)]
    
    task_contents = {}
    task_compressed = {}
    for task_path in task_paths:
        n = int(os.path.basename(task_path).removesuffix('.py').removeprefix('task'), 10)
        with open(task_path, 'rb') as f:
            data = f.read()
            if len(data) == 0: continue
            if b'p(g*2)' in data and not DO_GX2_SOLS: continue
            if data.startswith(b"#coding:l1"):
                new = data.decode('l1').removeprefix('#coding:l1\nimport zlib\nexec(zlib.decompress(bytes(')
                new = new.removesuffix(",'l1'),-9))")[1:-1].replace('\\\\', '\\\\').replace("\\0", '\x00').replace("\\n", '\x0a').replace("\\r", '\x0d').replace("\\'", "'").replace('\\"', '"')
                decompressed = zlib.decompress(new.encode('l1'), -9)
                try:
                    parse(decompressed); task_contents[n] = decompressed; task_compressed[n] = True
                except Exception as e: print(f"Failed to parse task {n:03d} due to {e}. Skipping")
                continue
            try:
                parse(data); task_contents[n] = data; task_compressed[n] = False
            except Exception as e: print(f"Failed to parse task {n:03d} due to {e}. Skipping")
    print("All sols loaded.")
    task_filtered = {tn: task_contents[tn] for tn in task_contents if DO_COMPRESSED_SOLS or (not task_compressed[tn])}

    tasks_to_run = []
    for task_num in task_filtered:
        code = autogolf.autogolf(task_contents[task_num].decode('l1'))
        tasks_to_run.append((task_num, code))
        if duplicate:
            for _ in range(99): tasks_to_run.append((task_num, code))
    
    random.shuffle(tasks_to_run)
    
    print(f"Starting parallel brute-force on {len(tasks_to_run)} tasks...")

    max_processes = os.cpu_count() - 1 or 1
    running_procs = {} 

    while tasks_to_run or running_procs:
        try:
            # 1. Launch new processes if there are open slots
            while len(running_procs) < max_processes and tasks_to_run:
                task_num, code = tasks_to_run.pop(0)
                print(f"v Spawning process for task {task_num:03d}...")
                process = multiprocessing.Process(target=charbrute, args=(task_num, code))
                process.start()
                running_procs[process] = (time.time(), task_num)

            # 2. Check the status of running processes
            finished_procs = []
            for process, (start_time, task_num) in running_procs.items():
                if not process.is_alive():
                    # Process finished on its own (completed or crashed)
                    print(f"^ Process for task {task_num:03d} finished cleanly.\n")
                    finished_procs.append(process)
                elif time.time() - start_time > TIMEOUT:
                    # Process timed out, so we terminate it
                    print(f"!! Terminating process for task {task_num:03d} (timeout > {TIMEOUT}s).")
                    process.terminate()
                    process.join()  # Wait for termination to complete
                    finished_procs.append(process)

            for process in finished_procs:
                del running_procs[process]
            time.sleep(0.1)
        except:
            for process, (start_time, task_num) in running_procs.items():
                process.terminate()
                process.join()
            exit('Quit.')

    print("All tasks have been processed.")

if __name__ == '__main__':
    main()
