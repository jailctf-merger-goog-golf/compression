from compression import get_compressed
from tqdm import trange
import warnings
import random
import re

# possible single letter varnames to use
VARNAMES = list("abcdefghijklmnopqrstuvwxyz")

VAR_PAT = re.compile(r"(?<!def )\b(?<!\"|')[a-zA-Z_](?!\"|')\b")

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
        compressed_code = get_compressed(brute_code, max_brute=3_000, use_tqdm=False, check_syntax=check_syntax)

    return brute_code, compressed_code

def do_brute(code: str | bytes, iterations: int, use_tqdm=True, log_best=True):
    code = code.strip()
    
    best_compressed = None
    best_bruted = None
    for i in (trange if use_tqdm else range)(iterations):
        # only check syntax on the first 10 to try to catch any outlier issues.
        # If that passes we stop checking syntax to speed it up
        bruted, compressed = do_rand_compress(code, i<10)
        if best_compressed is None or len(compressed) < len(best_compressed):
            if log_best:
                print(f"New Best {len(compressed)}!")
                print(bruted)
            best_bruted = bruted
            best_compressed = compressed

    return best_bruted, best_compressed

if __name__ == "__main__":
    code = r"""
import re
def p(a):
 b=[]
 for c in"0123456789".replace(d:=max(re.sub(", ","",str(a)),key=re.sub(", ","",str(a)).count),""):b+=re.findall(f"({c}+)(a*)({c}*)",re.sub(f'[{"0123456789".replace(c,"")}]',"a",re.sub(", ","",str(a))+re.sub(", ","",str([*zip(*a)]))));g={max([i,k],key=len)+d*len(j)+max([i,k],key=len) if k else i for i,j,k in b if{len(i),len(k)}-{1}};g=[s if len(s)!=2else s[0]*3for s in sorted({s for s in g if str(g).count(s)<2},key=len)]
 g=[d]*(len(g[0])>1)+g
 o=[len(max(g,key=len))*[0]for s in len(max(g,key=len))*[0]]
 p=0
 while g:q=[int(s)for s in g.pop()];o[p][p:p+len(q)]=o[~p][p:p+len(q)]=q;p+=1
 return[[*map(max,zip(*s))]for s in zip(o,zip(*o))]
"""

    bruted, compressed = do_brute(code, 1000)

    print("=" * 50)
    print(f"Best code | {len(bruted)}b => {len(compressed)}b\n{bruted}\n\n{compressed.hex()}")
    print("=" * 50)
