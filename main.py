import os
import tempfile
from sys import argv

def print_usage_and_exit():
    print(f"""
Usage: python3 {argv[0]} <list|run> [args...]

Example:
 - python3 {argv[0]} list
 - python3 {argv[0]} run v1
    """.strip())
    exit(1)


if len(argv) == 1:
    print_usage_and_exit()

OPTIONS_DIR = os.path.join(os.path.dirname(__file__), 'options')

option = argv[1]
if option == "list":
    print("\n".join(["* " + l for l in os.listdir(OPTIONS_DIR)]))
elif option == "run":
    if len(argv) != 3:
        print_usage_and_exit()
    if not os.path.exists(os.path.join(OPTIONS_DIR, argv[2])+'.py'):
        print('not found')
        exit(1)
    inp = bytes.fromhex(input('hex > '))
    with tempfile.NamedTemporaryFile(suffix='.py') as f:
        f.write(inp)
        f.flush()
        cmd='python3 '+os.path.join(OPTIONS_DIR, argv[2])+f'.py {f.file.name}'
        os.system(cmd)

