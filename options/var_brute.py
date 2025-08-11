from .compression import get_compressed
from tqdm import trange
import random
import re

# possible single letter varnames to use
VARNAMES = list("abcdefghijklmnopqrstuvwxyz")

VAR_PAT = re.compile(r"(?<!def )\b[a-zA-Z_]\b")

def do_rand_compress(code):
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
    compressed_code = get_compressed(brute_code, max_brute=3_000, use_tqdm=False)
    return brute_code, compressed_code

def do_brute(code: str | bytes, iterations: int, use_tqdm=True, log_best=True):
    code = code.strip()
    
    best_compressed = None
    best_bruted = None
    for _ in (trange if use_tqdm else range)(iterations):
        bruted, compressed = do_rand_compress(code)
        if best_compressed is None or len(compressed) < len(best_compressed):
            if log_best:
                print(f"New Best {len(compressed)}!")
                print(bruted)
            best_bruted = bruted
            best_compressed = compressed

    return best_bruted, best_compressed

if __name__ == "__main__":
    code = r"""
def p(g):
 Y=[0]+[l for l,m in enumerate(g)if max(m)<1]+[len(g)]
 X=[0]+[l for l,m in enumerate(zip(*g))if max(m)<1]+[len(g[0])]
 return[[max(max([g[l:m]for g in g[c:d]]))for l,m in zip(X,X[1:])]for c,d in zip(Y,Y[1:])]
"""

    bruted, compressed = do_brute(code, 100)

    print("=" * 50)
    print(f"Best code | {len(bruted)}b => {len(compressed)}b\n{bruted}\n\n{compressed.hex()}")
    print("=" * 50)
