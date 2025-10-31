from ast import *
import enum
import json
import autogolf
from os.path import join, dirname
import multiprocessing, os, zlib, itertools, random, time
from functools import lru_cache
from copy import deepcopy


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


@lru_cache
def test_code(task_num, code, return_on_first_fail=True) -> TestCodeStatus:
    task_num = task_num % 1000
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
    except:
        return TestCodeStatus.ERROR_UNRECOVERABLE
    if not hasattr(module, "p"):
        return TestCodeStatus.ERROR_UNRECOVERABLE
    program = getattr(module, "p")
    if not callable(program):
        return TestCodeStatus.ERROR_UNRECOVERABLE

    failed = False
    for tcnum in jsonfile_cache[task_num]:
        tc_data = jsonfile_cache[task_num][tcnum]
        inp = deepcopy(tc_data["input"])
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

def combined_mutation_gen(code: str, s_k: int = 1, d_k: int = 1, n: int = 10, charset: str = None, exclude_indices: list[int] = None):
    exclude_indices_set = set(exclude_indices if exclude_indices is not None else [0, 1, 2, 3, 4, 5])

    if charset is None:
        charset = code + code[6:]*4 + global_charnotset*3
    
    valid_indices = [i for i, char in enumerate(code) if i not in exclude_indices_set]
    lc = len(valid_indices)

    center_pcache = {}
    for i in range(lc):
        center_pcache[i] = [1/pow(abs(x-i)+1,1.5) for x in range(lc)]

    while True:
        mutated_code = code

        if 0 < s_k + d_k <= lc:
            s_k_temp = s_k
            d_k_temp = d_k
            if random.getrandbits(3) < 6:
                d_k_temp = random.randint(1, d_k - 1)
            if random.getrandbits(3) < 6:
                s_k_temp = random.randint(1, s_k - 1)
            
            center = random.randint(5, lc-3)
            affected_indices = []
            while len(affected_indices) < s_k_temp+d_k_temp:
                v = random.choices(valid_indices, center_pcache[center], k=1)[0]
                if v not in affected_indices:
                    affected_indices.append(v)

            del_indices = affected_indices[:d_k_temp]
            
            sub_map = {}
            for index in affected_indices[d_k_temp:]:
                sub_map[index] = random.choice(charset)

            new_code_list = []
            for i, char in enumerate(code):
                if i in del_indices:
                    continue
                elif i in sub_map:
                    if random.randint(0, 7) < 4: # do an insertion instead of a substitution sometimes
                        new_code_list.append(char)
                    new_code_list.append(sub_map[i])
                else:
                    new_code_list.append(char)
            
            mutated_code = "".join(new_code_list)

        final_code = mutated_code
        if len(final_code) >= len(code):
            continue

        if random.getrandbits(3) < 2:
            n = random.randint(1, 3)
        else:
            n = 0

        for _ in range(n):
                min_move_index = 0
                if exclude_indices_set:
                    min_move_index = max(exclude_indices_set) + 1

                if len(final_code) > min_move_index:
                    start = random.randint(min_move_index, len(final_code) - 1)
                    length = 1 # length = random.randint(1, n)
                    if random.getrandbits(3) < 3:
                        length = random.randint(1, 10)
                    end = min(start + length, len(final_code))
                    chunk = final_code[start:end]

                    remaining_code = final_code[:start] + final_code[end:]
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
global_charset = set("0123456789*+^><~-.,%/|& ")
global_charnotset = "".join(global_charset) + "   "

blacklist = {r"""p=lambda g,k=9:(r:=[*{x for x in sum(zip(*g),())if sum(g,g).count(x)==k}])and[r]*k or p(g,k-1)""",
             r"""def p(g):R=range(l:=len(B:=eval("[[8,*r,8]for r in zip(*"*2+"g"+")if 8in r]"*2)));return[[B[i][j]*[[*{c/8for c in sum(g,[])if c%8}][(i>j)+(~i+l<j)*2],0<i<l-1][i in(j,~j+l)]for j in R]for i in R]""",
             r"""p=lambda g,*x:[*{i for i in zip(*x or p(*g))if any(i)}]""",
            }

# modify this function to do stuff
def charbrute(task_num, code):
    import warnings
    warnings.filterwarnings("ignore")

    original_len = len(code)

    for final in combined_mutation_gen(code, 4, 3, 0):
        if test_code(task_num, final) == TestCodeStatus.SUCCESS:
            try:
                final = autogolf.autogolf(final)
            except:
                pass

            if final not in blacklist and (task_num % 1000 != 238 or ":0for" in final):
                
                golfed_len = len(final)

                if golfed_len < original_len:
                    with open('brute.txt', 'r') as f:
                        if final in f.read(): continue
                    print(f"hit on t{task_num:03d} ({original_len} -> {golfed_len}): {final}" + "!"*100)
                    with open('brute.txt', 'a') as f:
                        f.write(f"new best on t{task_num:03d} ({original_len} -> {golfed_len}): {final}\n")


def main():
    import warnings
    warnings.filterwarnings("ignore")

    TEST_EXPORT_DIR_PATH = r"../../../../all_sols/"
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
        if ".DS_Store" in task_path:
            continue
        n = int(os.path.basename(task_path).removesuffix('.py').removeprefix('task').lstrip('v'), 10)
        n += task_path.count('v') * 1000
        with open(task_path, 'rb') as f:
            data = f.read()
            if len(data) == 0: continue
            if b'p(g*2)' in data and not DO_GX2_SOLS: continue
            if data.startswith(b"#coding:l1"):
                new = data.decode('l1').removeprefix('#coding:l1\nimport zlib\nexec(zlib.decompress(bytes(').removeprefix('#coding:l1\nimport zlib,re\nexec(zlib.decompress(bytes(')
                new = new.removesuffix(",'l1'),-9))")[1:-1].replace('\\\\', '\\\\').replace("\\0", '\x00').replace("\\n", '\x0a').replace("\\r", '\x0d').replace("\\'", "'").replace('\\"', '"')
                decompressed = zlib.decompress(new.encode('l1'), -9)
                try:
                    task_compressed[n] = True; parse(decompressed); task_contents[n] = decompressed
                except Exception as e: print(f"Failed to parse task {n:03d} due to {e}. Skipping")
                continue
            try:
                parse(data); task_contents[n] = data; task_compressed[n] = False
            except Exception as e: print(f"Failed to parse task {n:03d} due to {e}. Skipping")
    print("All sols loaded.")
    task_filtered = {tn: task_contents[tn] for tn in task_contents if DO_COMPRESSED_SOLS or (not task_compressed[tn])}

    task_filtered = {}
    
    base = 305
    
    task_filtered[base] = rb"""p=lambda g,x=2:g*0!=0and[p(r,x:=x-1)or-x%max(g)+1for r in g]"""

#     sols = rb"""p=lambda g:g and[x:=[3]*len(g),g[2:]and[*g[0][1:],3]or x,*zip(*p([*zip(*g[2:])])[::-1])]
# p=lambda g:g and[x:=[3]*len(g),g[2:]and[*g[2][1:],3]or x,*zip(*p([*zip(*g[2:])])[::-1])]
# p=lambda g:g and[x:=[3]*len(g),x[2:]and[*g[0][1:],3]or x,*zip(*p([*zip(*g[2:])])[::-1])]
# p=lambda g:g and[[3]*len(g),g[2:]and[*g[0][1:],3]or[3,3],*zip(*p([*zip(*g[2:])])[::-1])]
# """.strip().splitlines()

    # for i,sol in enumerate(sols):
    #     task_filtered[base + i*1000] = sol

    tasks_to_run = []
    for task_num in task_filtered:
        try:
            code = autogolf.autogolf(task_filtered[task_num].decode('l1'))
        except:
            print(task_filtered[task_num])
        tasks_to_run.append((task_num, code))
        if duplicate:
            for _ in range(99): tasks_to_run.append((task_num, code))
    
    random.shuffle(tasks_to_run)
    
    print(f"Starting parallel brute-force on {len(tasks_to_run)} tasks...")

    max_processes = 8
    # max_processes = os.cpu_count() - 1 or 1
    running_procs = {}

    while tasks_to_run or running_procs:
        try:
            # 1. Launch new processes if there are open slots
            while len(running_procs) < max_processes and tasks_to_run:
                task_num, code = tasks_to_run.pop()
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
