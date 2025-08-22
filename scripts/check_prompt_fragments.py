#!/usr/bin/env python3
import re
import sys

PROMPT_PATTERN = re.compile(r"^(?:\s*(?:>>>|\.\.\.|\$) |.*root@.*#.*|.*workspace#.*)")


def main() -> int:
    failed = False
    for path in sys.argv[1:]:
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                for lineno, line in enumerate(handle, 1):
                    if PROMPT_PATTERN.search(line):
                        print(f"{path}:{lineno}: contains shell prompt fragment")
                        failed = True
        except OSError as exc:
            print(f"{path}: {exc}")
            failed = True
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
