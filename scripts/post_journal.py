"""학습 기록 파일(docx, txt, md)을 해당 장 이슈에 댓글로 단다(로컬에서 본인 gh 인증으로 실행).

사용법: python scripts/post_journal.py <이슈 번호> <파일> [--dry-run]
원본은 private/journal_src/<날짜>_<파일 이름>으로 복사한다. 내용은 바꾸지 않는다.
"""
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "private" / "journal_src"


def to_markdown(path):
    ext = path.suffix.lower()
    if ext == ".docx":
        return subprocess.run(["pandoc", str(path), "-t", "gfm", "--wrap=none"], capture_output=True, text=True, check=True, encoding="utf-8").stdout
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    sys.exit("지원하지 않는 형식: " + ext)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    issue, path = sys.argv[1], Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    today = datetime.date.today().isoformat()
    body = f"{today} 학습 기록 (원본: {path.name})\n\n" + to_markdown(path).strip() + "\n"
    check = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_public.py"), "text"], input=body, capture_output=True, text=True, encoding="utf-8")
    if check.returncode:
        sys.exit("공개 검사에 걸려 올리지 않았다:\n" + check.stdout)
    if dry:
        print(body)
        return
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, SRC_DIR / f"{today}_{path.name}")
    subprocess.run(["gh", "issue", "comment", issue, "--body-file", "-"], input=body, cwd=ROOT, text=True, encoding="utf-8", check=True)
    print("댓글 등록:", issue)


if __name__ == "__main__":
    main()
