import os
import tempfile
from sys import argv

def print_usage_and_exit():
    print(f"""
Usage: python3 {argv[0]} <list|run|var_brute> [args...]

Example:
 - python3 {argv[0]} list
 - python3 {argv[0]} run v1
 - python3 {argv[0]} var_brute 100
    """.strip())
    exit(1)


if len(argv) == 1:
    print_usage_and_exit()

OPTIONS_DIR = os.path.join(os.path.dirname(__file__), 'options')

option = argv[1]
if option == "list":
    print("\n".join(["* " + l for l in os.listdir(OPTIONS_DIR)]))
elif option == "run":
    from options.compression import get_compressed

    if len(argv) != 3:
        print_usage_and_exit()

    inp = bytes.fromhex(input('hex > '))
    
    run_type = argv[2]
    if run_type == 'compression-v1':
        compressed = get_compressed(inp, max_brute=10_000, use_tqdm=False)
    elif run_type == 'compression-v1-fast':
        compressed = get_compressed(inp, max_brute=3_000, use_tqdm=False)
    else:
        raise ValueError(f"Unknown compression type of {run_type!r}")
    
    print(compressed.hex())
elif option == "var_brute":
    from options.var_brute import do_brute
    
    num_iters = int(argv[2])
    inp = bytes.fromhex(input('hex > '))
    
    best_code, best_compressed = do_brute(inp, num_iters, use_tqdm=False, log_best=False)
    print(best_compressed.hex())