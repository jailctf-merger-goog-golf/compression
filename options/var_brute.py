from compression import get_compressed 
from tqdm import trange
import warnings
import random
import re
from sys import argv

# possible single letter varnames to use
VARNAMES = list("abcdefghijklmnoqrstuvwxyz")

VAR_PAT = re.compile(r"\b(?<!\"|'|%)(?!p\()[a-zA-Z_](?!\"|')\b(?<!def p)")

def do_rand_compress(code, check_syntax=False):
    global VARNAMES, VAR_PAT
    mapping = {}
    shuffled_varnames = VARNAMES.copy()
    random.shuffle(shuffled_varnames)
    
    def update(m: re.Match[str]):
        nonlocal mapping, shuffled_varnames
        var = m[0]
        if var in mapping:
            return mapping[var]
        
        next_var = shuffled_varnames.pop()
        mapping[var] = next_var
        return next_var
    
    brute_code = re.sub(VAR_PAT, update, code)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=SyntaxWarning)
        compressed_code = get_compressed(brute_code, max_brute=1_000, use_tqdm=False, check_syntax=check_syntax)

    return brute_code, compressed_code, mapping

def do_brute(code: str | bytes, iterations: int, use_tqdm=True, log_best=True):
    global VARNAMES
    code = code.strip()
    
    _, _, mapping = do_rand_compress(code, False)
    VARNAMES = list("abcdefghijklmnopqrstuvwxyz")#[1:len(mapping)+1]
    
    best_compressed = None
    best_bruted = None
    for i in (trange if use_tqdm else range)(iterations):
        # only check syntax on the first 10 to try to catch any outlier issues.
        # If that passes we stop checking syntax to speed it up
        bruted, compressed, _ = do_rand_compress(code, i<10)
        if best_compressed is None or len(compressed) < len(best_compressed):
            if log_best:
                print(f"New best {len(code)}b => {len(compressed)}b!")
                print(bruted)
                print()
                print(compressed.hex())
                print('=' * 50)
            best_bruted = bruted
            best_compressed = compressed

    return best_bruted, best_compressed

if __name__ == "__main__":
    code = r"""
def p(e):
 for u,b in enumerate(e):
  for r,i in enumerate(b):
   for t,*b in b"lump",b"ltp",b"lur":
    try:
     for f in b:e[u+f%4][r+f%3]&4or l
     for f in b:e[u+f%4][r+f%3]=t
     if p(e):return e
     for f in b:e[u+f%4][r+f%3]=5
    except:e
   if i&4:return 
 return e
"""
    if len(argv) > 1:
        code = bytes.fromhex(argv[1]).decode('l1')

    bruted, compressed = do_brute(code, 100_000)

    print("=" * 50)
    print(f"Best code | {len(bruted)}b => {len(compressed)}b\n{bruted}\n\n{compressed.hex()}")
    print("=" * 50)
