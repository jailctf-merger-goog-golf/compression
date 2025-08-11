import zlib
from zopfli.zlib import compress as zopfli_compress
from tqdm import tqdm, trange
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

def make_code(compressed: bytes, add_wbits: bool, least_quote: int, most_quote: str):
    # do the repr manually
    code_str = b""
    for char in compressed:
        match char:
            case 0:
                code_str += b"\\0"
            case 0xa:
                code_str += b"\\n"
            case 0xd:
                code_str += b"\\r"
            case 0x27 | 0x22:
                if char == least_quote:
                    code_str += f"\\{least_quote:c}".encode()
                else:
                    code_str += most_quote.encode()
            case 0x5c:
                code_str += b"\\\\"
            case _:
                code_str += bytes([char])
    
    code_str = fix_backslashes(code_str)
    new_code = f"#coding:l1\nimport zlib\nexec(zlib.decompress(bytes({least_quote:c}".encode() + \
               code_str + \
               f"{least_quote:c},'l1'){',-9' if add_wbits else ''}))".encode()
    
    return new_code

def get_compressed(code: str | bytes, filename=None, max_brute=10_000, use_tqdm=True):
    code = code.strip()
    
    if isinstance(code, str):
        code = code.encode("utf-8")
    
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        e.add_note("! **********\nYour code has a syntax error, fix it.\n! **********")
        raise
    
    possible = [
        (zlib.compress(code), False),
        (zlib.compress(code, wbits=-15), True),
        *[(zopfli_compress(code, numiterations=iters)[2:-4], True) for iters in (trange if use_tqdm else range)(1_000, max_brute, 1_000)]
    ]

    best = None
    for compressed, add_wbits in possible:
        least_quote = min(*b"'\"", key=compressed.count)
        most_quote = "'\""[least_quote == b"'"[0]]
        
        cur_code = make_code(compressed, add_wbits, least_quote, most_quote)
        if best is None or len(cur_code) < len(best):
            best = cur_code
    
    assert best is not None, "Unable to find best?"

    orig_len = len(code)
    new_len = len(best)
    if new_len > orig_len:
        print("WARNING: compressed version is longer than decompressed version", file=sys.stderr)
        
    if filename is not None:
        with open(filename, "wb") as f:
            f.write(best)
    
    return best