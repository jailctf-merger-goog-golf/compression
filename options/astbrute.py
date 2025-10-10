import enum
import json
from ast import *
import autogolf
from os.path import join, dirname
import os
import zlib
import multiprocessing

_const_node_type_names = {
    bool: 'NameConstant',  # should be before int
    type(None): 'NameConstant',
    int: 'Num',
    float: 'Num',
    complex: 'Num',
    str: 'Str',
    bytes: 'Bytes',
    type(...): 'Ellipsis',
}

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


def nuke_nodes_gen(ast):
    """a.k.a node deletion operation"""

    class NodeTransformerGenerator:
        def visit(self, node, root_node=True):
            """Visit a node."""
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            for new_field, new_value in visitor(node):
                new_self = node.__class__()  # epic philosophy moment
                for old_field, old_value in iter_fields(node):
                    setattr(new_self, old_field, old_value)
                # print(len(inspect.stack(0)), f"visit ({node=})", root_node, new_field, new_value)
                # either way we yield up the call stack
                if new_value is None:  # delete this node so yield
                    delattr(new_self, new_field)
                else:  # the node below is modified so yield with modifications
                    setattr(new_self, new_field, new_value)
                yield new_self

        def generic_visit(self, node):
            # print('Enter', node)
            for field, old_value in iter_fields(node):
                if (field, type(node)) in SKIP_FIELD_NODES_COMBOS:  # lame ass fields
                    continue
                if isinstance(old_value, list):
                    for i, value in enumerate(old_value):
                        if isinstance(value, AST):
                            res = self.visit(value, False)
                            for yielded in res:
                                yield field, old_value[:i] + [yielded] + old_value[i+1:]
                            yield field, old_value[:i] + old_value[i+1:]
                elif isinstance(old_value, Constant):
                    yield field, None
                elif isinstance(old_value, AST):  # AST class = superclass of all ast node classes
                    visit_res = self.visit(old_value, False)
                    for possibility2 in visit_res:
                        yield field, possibility2
                    yield field, None
            # print("Exit", node)

        def visit_Constant(self, node):
            value = node.value
            type_name = _const_node_type_names.get(type(value))
            if type_name is None:
                for cls, name in _const_node_type_names.items():
                    if isinstance(value, cls):
                        type_name = name
                        break
            if type_name is not None:
                method = 'visit_' + type_name
                try:
                    visitor = getattr(self, method)
                except AttributeError:
                    pass
                else:
                    import warnings
                    warnings.warn(f"{method} is deprecated; add visit_Constant",
                                  DeprecationWarning, 2)
                    return visitor(node)
            return self.generic_visit(node)
    yield from NodeTransformerGenerator().visit(ast)


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
    except (SyntaxError, TypeError):
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
        res = json.loads(json.dumps(res).replace("true", "1").replace("false", "0"))
        if res != out:
            failed = True
            if return_on_first_fail:

                return TestCodeStatus.TC_FAIL
    if failed:
        return TestCodeStatus.TC_FAIL
    return TestCodeStatus.SUCCESS


def test_ast(task_num, ast):
    # noinspection PyBroadException
    try:
        code = autogolf.autogolf_unsafe(ast)
    except Exception as e:
        return TestCodeStatus.ERROR_UNRECOVERABLE

    res = test_code(task_num, code)

    return res


def astbrute(task_num, ast):
    # print(dump(ast))
    best_code = autogolf.golfed_unparse_unsafe(ast)
    # print(f"Cur Best ({len(best_code):03d}b): {best_code}")
    # print('===')
    # for new_ast in nuke_nodes_gen(parse("print('abc'[0:2])")):

    made_improvement = False
    for new_ast in nuke_nodes_gen(ast):
        # print('new_ast', dump(new_ast))
        result = test_ast(task_num, new_ast)
        if result == TestCodeStatus.SUCCESS:
            new_code = autogolf.golfed_unparse_unsafe(new_ast)
            if len(new_code) < len(best_code):
                best_code = new_code
                print(f"New best (t{task_num:03d}, {len(new_code):03d}b): {new_code}")
                made_improvement = True
        else:
            # print(result)
            pass
    if not made_improvement:
        print(f"no improvements to t{task_num:03d}")


def main():
    import warnings
    warnings.filterwarnings("ignore")

    TEST_EXPORT_DIR_PATH = r"C:\Users\quasar\Downloads\export-1760061589"
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

    for task_num in task_contents:
        if (not DO_COMPRESSED_SOLS) and task_compressed[task_num]:
            continue
        code = autogolf.autogolf(task_contents[task_num].decode('l1'))
        astbrute(task_num, parse(code))


if __name__ == '__main__':
    main()
