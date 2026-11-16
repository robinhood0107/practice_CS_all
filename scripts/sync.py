"""장 파일마다 이슈를 만들고 README 표를 다시 만든다(로컬에서 본인 gh 인증으로 실행).

장 파일: courses/<과목 폴더>/<NN>_<이름>.md (README.md 제외)
장 파일 첫 줄의 '<!-- issue: N -->'에 이슈 번호를 기록한다.
과목 폴더의 README.md 첫 줄 '# 제목'을 과목 이름으로 쓴다.

사용법: python scripts/sync.py [--dry-run]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COURSES = ROOT / "courses"
MARK = re.compile(r"^<!-- issue: (\d+) -->\n?")
DRY = "--dry-run" in sys.argv


def gh(*args, inp=None):
    return subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True, check=True, input=inp).stdout


def repo():
    return json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]


def course_title(folder):
    readme = folder / "README.md"
    if readme.exists():
        first = readme.read_text(encoding="utf-8").splitlines()[0]
        return first.lstrip("# ").strip()
    return folder.name


def chapter_title(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def ensure_label(name):
    if not DRY:
        subprocess.run(["gh", "label", "create", name, "--force", "--color", "0E8A16"], cwd=ROOT, capture_output=True)


def chapters():
    for folder in sorted(p for p in COURSES.iterdir() if p.is_dir()):
        for path in sorted(folder.glob("[0-9][0-9]_*.md")):
            yield folder, path


def sync_issues():
    full = repo()
    for folder, path in chapters():
        text = path.read_text(encoding="utf-8")
        if MARK.match(text):
            continue
        course = course_title(folder)
        title = f"[{course}] {chapter_title(path)}"
        rel = path.relative_to(ROOT).as_posix()
        body = f"학습 자료: https://github.com/{full}/blob/main/{rel}\n\n이 장의 학습 기록을 댓글로 남긴다."
        ensure_label(course)
        if DRY:
            print("이슈 생성 예정:", title)
            continue
        url = gh("issue", "create", "--title", title, "--body", body, "--label", course).strip()
        num = url.rstrip("/").split("/")[-1]
        path.write_text(f"<!-- issue: {num} -->\n" + text, encoding="utf-8")
        print("이슈 생성:", num, title)


def update_readme():
    states = {}
    if not DRY:
        for it in json.loads(gh("issue", "list", "--state", "all", "--limit", "1000", "--json", "number,state")):
            states[it["number"]] = it["state"]
    lines = ["# practice_CS_all", "", "CS, 언어, DB, 인프라 학습 기록. 장마다 이슈 하나에 학습 기록을 남긴다.", ""]
    total = done = 0
    by_course = {}
    for folder, path in chapters():
        by_course.setdefault(folder, []).append(path)
    for folder, paths in by_course.items():
        rows = []
        cdone = 0
        for path in paths:
            m = MARK.match(path.read_text(encoding="utf-8"))
            num = int(m.group(1)) if m else None
            state = states.get(num, "") if num else ""
            closed = state == "CLOSED"
            cdone += closed
            issue = f"[#{num}](../../issues/{num})" if num else "-"
            rel = path.relative_to(ROOT).as_posix()
            rows.append(f"| [{chapter_title(path)}]({rel}) | {issue} | {'완료' if closed else '진행 중' if num else '이슈 없음'} |")
        total += len(paths)
        done += cdone
        lines += [f"## {course_title(folder)} ({cdone}/{len(paths)})", "", "| 장 | 이슈 | 상태 |", "|---|---|---|", *rows, ""]
    lines.insert(4, f"전체 진행: {done}/{total}\n")
    out = "\n".join(lines)
    if DRY:
        print(out)
    else:
        (ROOT / "README.md").write_text(out, encoding="utf-8")
        print("README 갱신")


if __name__ == "__main__":
    sync_issues()
    update_readme()
