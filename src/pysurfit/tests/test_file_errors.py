"""A failed file autoload must leave a diagnostic, not an empty task.

The loader chain still probes the next format, but a malformed file and a
missing file must each produce a warning through the log hook.

  python3 test_file_errors.py
"""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    messages = []
    surfit.set_log_handler(lambda level, message: messages.append(message))
    try:
        with tempfile.TemporaryDirectory() as directory:
            missing = os.path.join(directory, "missing.xyz")
            surfit.file_load(missing)
            malformed = os.path.join(directory, "broken.grd")
            with open(malformed, "w", encoding="ascii") as stream:
                stream.write("CDF\x01garbage\n")
            surfit.file_load(malformed)
    finally:
        surfit.clear_log_handler()
    assert any("file_load" in message or "auto_load" in message
               for message in messages), messages
    assert any("missing.xyz" in message for message in messages), messages
    print("PASS: failed autoload reports a diagnostic")


if __name__ == "__main__":
    main()
