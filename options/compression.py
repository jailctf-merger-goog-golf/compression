import zlib
from zopfli.zlib import compress as zopfli_compress # type: ignore
from tqdm import tqdm, trange # pyright: ignore[reportMissingModuleSource]
import re
import sys


def fix_backslashes(code_str: bytes):
    # update to keep invalid escape sequences to compress even further
    def update(m: re.Match[bytes]):
        data = m[0]
        if data[2] in b"\\'\"abfnNrtuUvox01234567879":
            return data
        return bytes((data[0], data[2]))

    return re.sub(br"\\\\.", update, code_str)


def make_code(compressed: bytes, add_wbits: bool, least_quote: int, most_quote: int):
    # do the repr manually
    code_str = []
    for char in compressed:
        match char:
            case 0:
                code_str += [92, 48]
            case 0xa:
                code_str += [92, 110]
            case 0xd:
                code_str += [92, 114]
            case 0x27 | 0x22:
                if char == least_quote:
                    code_str += [92, least_quote]
                else:
                    code_str += [most_quote]
            case 0x5c:
                code_str += [92, 92]
            case _:
                code_str += [char]
    
    # code_str += [compressed[-1] | 0x80]

    code_str = fix_backslashes(bytes(code_str))
    new_code = f"#coding:l1\nimport zlib\nexec(zlib.decompress(bytes({least_quote:c}".encode() + \
               code_str + \
               f"{least_quote:c},'l1'){',-9' if add_wbits else ''}))".encode()

    return new_code

def make_code_X(compressed: bytes, add_wbits: bool, least_quote: int, most_quote: int):
    
    return make_code(compressed, add_wbits, least_quote, most_quote), len(compressed)


def get_compressed(code: str | bytes, filename=None, max_brute=10_000, use_tqdm=True, check_syntax=True):
    code = code.strip()

    if isinstance(code, str):
        code = code.encode("utf-8")

    if check_syntax:
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            e.add_note("! **********\nYour code has a syntax error, fix it.\n! **********")
            raise

    possible = [
        (zlib.compress(code), False),
        (zlib.compress(code, wbits=-15), True),
        *[(zopfli_compress(code, numiterations=iters or 15)[2:-4], True) for iters in
          (trange if use_tqdm else range)(0, max_brute, 1_000)]
    ]

    best = None
    for compressed, add_wbits in possible:
        least_quote = min(*b"'\"", key=compressed.count)
        most_quote = b"'\""[least_quote == b"'"[0]]

        cur_code = make_code(compressed, add_wbits, least_quote, most_quote)
        if best is None or len(cur_code) < len(best):
            best = cur_code

    assert best is not None, "Unable to find best?"

    orig_len = len(code)
    new_len = len(best)
    if new_len > orig_len and __name__ == "__main__":
        print("WARNING: compressed version is longer than decompressed version", file=sys.stderr)

    if filename is not None:
        with open(filename, "wb") as f:
            f.write(best)

    return best

def get_compressed_X(code: str | bytes, filename=None, max_brute=10_000, use_tqdm=True, check_syntax=True):
    code = code.strip()

    if isinstance(code, str):
        code = code.encode("utf-8")

    if check_syntax:
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            e.add_note("! **********\nYour code has a syntax error, fix it.\n! **********")
            raise

    possible = [
        (zlib.compress(code), False),
        (zlib.compress(code, wbits=-15), True),
        *[(zopfli_compress(code, numiterations=iters or 15)[2:-4], True) for iters in
          (trange if use_tqdm else range)(0, max_brute, 1_000)]
    ]

    best = None
    for compressed, add_wbits in possible:
        least_quote = min(*b"'\"", key=compressed.count)
        most_quote = b"'\""[least_quote == b"'"[0]]

        cur_code, raw_len = make_code_X(compressed, add_wbits, least_quote, most_quote)
        if best is None or raw_len < best[1]:
            best = (cur_code, raw_len)

    assert best is not None, "Unable to find best?"

    orig_len = len(code)
    new_len = len(best[0])
    if new_len > orig_len and __name__ == "__main__":
        print("WARNING: compressed version is longer than decompressed version", file=sys.stderr)

    if filename is not None:
        with open(filename, "wb") as f:
            f.write(best[0])

    return best


if __name__ == "__main__":
    code = r"""
import re
def p(s):t=f'{s+[*zip(*s)]}';n=re.sub("[, ]","",t+t[::-1]);r={e+max(n,key=t.count)*len(r)+e if r else 3*f for e,f,r in re.findall(r"(?=(([^%s])\2+)((?:\d)*?)\2)"%max(n,key=t.count),n)};r=[max(n,key=t.count)]+[f for f in{*t}if t.count(f)==2]+[3*f for f in{*t}if t.count(f)==6]+sorted({f for f in r if str(r).count(f)==1},key=len);return[[int(r[~min(e,len(r[-1])+~e,f,len(r[-1])+~f)][min(abs(e-f),abs(len(r[-1])+~e-f))])for f in range(len(r[-1]))]for e in range(len(r[-1]))]
"""

    compressed = get_compressed(code)
    print(f"Done! {len(code.strip())}b => {len(compressed)}b\n")
    print(compressed.hex())
