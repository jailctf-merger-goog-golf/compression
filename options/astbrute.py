import enum
import json
from ast import *
import autogolf
from os.path import join, dirname
import warnings
import inspect
warnings.filterwarnings("ignore")

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
DEBUG = False


def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


class TestCodeStatus(enum.Enum):
    SUCCESS = 0
    TC_FAIL = 1
    ERROR = 2


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
                if field in ["type_ignores"]:  # lame ass fields
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
    exec(code, module.__dict__)
    assert hasattr(module, "p"), "Error: Unable to locate function p() in task.py."
    program = getattr(module, "p")
    assert callable(program), "Error: Function p() in task.py is not callable."

    failed = False
    for tcnum in jsonfile_cache[task_num]:
        tc_data = jsonfile_cache[task_num][tcnum]
        inp = tc_data["input"]
        out = tc_data["output"]
        res = json.loads(json.dumps(program(inp)).replace("true", "1").replace("false", "0"))
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
        res = autogolf.autogolf_unsafe(ast)
    except Exception as e:
        print(e)
        return -3
    return test_code(task_num, res)


def astbrute(task_num, ast):
    # print(dump(ast))
    # print(test_ast(task_num, ast))
    # for variation in nuke_nodes_gen(parse("print('abc'[0:2])")):
    for variation in nuke_nodes_gen(ast):
        print('variation', dump(variation))
        print(test_ast(task_num, variation))


def main():
    task_num = 98
    code = "p=lambda g,x=[],z=[]:g*0!=0and[*map(p,g,g[0:1]+x+g,(z+g)[1:]+g)]or(x*z<1)*g"
    #       p=lambda g,x=[],z=[]:g*0!=0and[*map(p,g,g[:1]+x+g,(z+g)[1:]+g)]or(x*z<1)*g

    task_num = 150
    code = "p=lambda g:[r[0::-1]for r in g]"
    astbrute(task_num, parse(code))


if __name__ == '__main__':
    main()
