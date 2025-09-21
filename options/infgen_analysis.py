import os
import subprocess
import tempfile
import zlib

INFGEN_BINARY = os.path.join(os.path.dirname(__file__), 'infgen')


__all__ = ["infgen_call"]


def infgen_call(data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(data)
        f.flush()
        try:
            proc = subprocess.run([INFGEN_BINARY, '-m', '-dd', f.name], capture_output=True, timeout=2, text=True, encoding='latin-1')
            if proc.returncode != 0:
                msg = '!! FAIL !!\n\n' + proc.stderr + '====\n' + proc.stdout
            else:
                msg = proc.stdout
        except subprocess.TimeoutExpired:
            msg = f"infgen binary timed out after 2 seconds."
        except Exception as e:
            msg = repr(e)

    return msg


def main():
    print(infgen_call(zlib.compress(b'qwdqwdqwd123123123qwdqwdqwd',wbits=-9)))


if __name__ == '__main__':
    main()
