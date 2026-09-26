"""Подготовка «крупного» репозитория для проверки (ТЗ 9.2: ≥10 000 файлов или ≥20 000 коммитов).

Создаёт локальный git-репозиторий через `git fast-import` (секунды вместо часов):
  * FILES исходных файлов (по умолчанию 12 000) в дереве каталогов, часть с TODO/FIXME;
  * COMMITS коммитов (по умолчанию 20 500), растянутых по датам на ~3 года - старые маркеры
    появляются в ранних коммитах, свежие - в последних месяцах.

Использование:
  python scripts/make_large_repo.py ./large-repo [--files 12000] [--commits 20500]
  cd large-repo && git remote add origin https://git.sourcecraft.dev/<org>/<repo>.git && git push -u origin main

После пуша - «Проанализировать» по ссылке на странице рейтинга или `python -m app.cli analyze <org>/<repo>`.
"""

import argparse
import random
import subprocess
import time
from pathlib import Path

DAY = 86400


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--files", type=int, default=12000)
    parser.add_argument("--commits", type=int, default=20500)
    args = parser.parse_args()

    repo = Path(args.path)
    repo.mkdir(parents=True, exist_ok=False)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)

    rnd = random.Random(42)
    now = int(time.time())
    start = now - 3 * 365 * DAY
    step = (now - start) // args.commits
    stream = []
    mark = 0

    def blob(content: str) -> int:
        nonlocal mark
        mark += 1
        data = content.encode()
        stream.append(f"blob\nmark :{mark}\ndata {len(data)}\n".encode() + data + b"\n")
        return mark

    def file_body(i: int, version: int, with_marker: bool) -> str:
        lines = [f"def func_{i}_{j}(x):\n    return x * {j} + {version}\n" for j in range(12)]
        if with_marker:
            lines.insert(3, f"# {'TODO' if i % 2 else 'FIXME'}: revisit module {i}\n")
        return "".join(lines)

    # Первый коммит - все файлы; маркеры в 3% файлов (старые, т.к. коммит 3 года назад).
    files = [f"pkg{i % 50}/sub{i % 7}/module_{i}.py" for i in range(args.files)]
    commit_lines = [b"commit refs/heads/main\n", f"committer Gen <gen@example.com> {start} +0000\n".encode(),
                    b"data 7\ninitial\n"]
    for i, path in enumerate(files):
        m = blob(file_body(i, 0, i % 33 == 0))
        commit_lines.append(f"M 100644 :{m} {path}\n".encode())
    readme = blob("# Large repo\n\n## Installation\n\npip install -e .\n\n## Tests\n\npytest\n")
    commit_lines.append(f"M 100644 :{readme} README.md\n".encode())
    stream.append(b"".join(commit_lines) + b"\n")

    for c in range(1, args.commits):
        ts = start + c * step
        i = rnd.randrange(args.files)
        fresh_marker = ts > now - 120 * DAY and rnd.random() < 0.05
        m = blob(file_body(i, c, fresh_marker or i % 33 == 0))
        msg = f"change {c}".encode()
        stream.append(b"commit refs/heads/main\n" + f"committer Dev{c % 9} <dev{c % 9}@example.com> {ts} +0000\n".encode()
                      + f"data {len(msg)}\n".encode() + msg + b"\n" + f"M 100644 :{m} {files[i]}\n\n".encode())

    subprocess.run(["git", "fast-import", "--quiet"], cwd=repo, input=b"".join(stream), check=True)
    subprocess.run(["git", "checkout", "-q", "main"], cwd=repo, check=True)
    count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    print(f"{repo}: files={args.files + 1}, commits={count}")


if __name__ == "__main__":
    main()
