"""Create a disposable, minimal StarDict fixture for local sdcv smoke tests."""

import argparse
import struct
from pathlib import Path


def create_fixture(data_dir):
    """Create one English-to-Traditional-Chinese entry under ``data_dir/dic``."""
    dictionary_dir = Path(data_dir) / "dic"
    dictionary_dir.mkdir(parents=True, exist_ok=True)
    word = b"zorb"
    definition = "虛構測試用英中詞條".encode("utf-8")
    index = word + b"\0" + struct.pack("!II", 0, len(definition))
    base = dictionary_dir / "englex-smoke"
    base.with_suffix(".dict").write_bytes(definition)
    base.with_suffix(".idx").write_bytes(index)
    base.with_suffix(".ifo").write_text(
        "StarDict's dict ifo file\n"
        "version=2.4.2\n"
        "bookname=englex smoke fixture\n"
        "wordcount=1\n"
        f"idxfilesize={len(index)}\n"
        "sametypesequence=m\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir")
    create_fixture(parser.parse_args().data_dir)
