"""Run reproducible checks and save real subprocess output as UTF-8."""

import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True)
    for filename, arguments in [
        ("test_output.txt", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("demo_output.txt", ["main.py", "--demo"]),
        ("evaluation_output.txt", ["scripts/evaluate.py"]),
    ]:
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True, text=True)
        (output / filename).write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"{' '.join(arguments)}: exit {result.returncode}; saved outputs/{filename}")
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
    # Independently validate PNG framing, checksums, decompression and pixel size.
    paths = list((ROOT / "datasets/images").glob("*.png"))
    for path in paths:
        blob = path.read_bytes()
        assert blob[:8] == b"\x89PNG\r\n\x1a\n", path
        offset, compressed = 8, b""
        while offset < len(blob):
            size = struct.unpack(">I", blob[offset:offset+4])[0]
            kind = blob[offset+4:offset+8]
            payload = blob[offset+8:offset+8+size]
            crc = struct.unpack(">I", blob[offset+8+size:offset+12+size])[0]
            assert zlib.crc32(kind + payload) == crc, path
            if kind == b"IHDR":
                width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
                assert width > 0 and height > 0, path
                assert (depth, color, compression, filtering, interlace) == (8, 2, 0, 0, 0), path
            if kind == b"IDAT":
                compressed += payload
            offset += 12 + size
        assert len(zlib.decompress(compressed)) == height * (1 + width * 3), path
        assert kind == b"IEND", path
    print(f"Validated {len(paths)} RGB PNG files.")
    demo = subprocess.run([sys.executable, str(ROOT / "main.py"), "--demo", "--top-k", "1"], cwd=ROOT.parent, capture_output=True, text=True)
    assert demo.returncode == 0, demo.stderr
    print("Demo also passed from the parent working directory.")
    invalid = subprocess.run([sys.executable, "main.py", "--top-k", "0"], cwd=ROOT, capture_output=True, text=True)
    assert invalid.returncode == 1 and "positive integer" in invalid.stderr
    menu = subprocess.run([sys.executable, "main.py"], cwd=ROOT, input="3\nlist\n4\n3\n0\n", capture_output=True, text=True)
    assert menu.returncode == 0 and "query_c.png" in menu.stdout and "stock: 0" in menu.stdout
    print("CLI invalid top-k, image listing, product details and exit checks passed.")


if __name__ == "__main__":
    main()
