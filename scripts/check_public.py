"""공개 저장소에 올라가면 안 되는 경로, 크기, 문구, 표기를 검사한다.

사용법
  python scripts/check_public.py files          추적, 스테이징된 파일 전체 검사
  python scripts/check_public.py msg FILE       커밋 메시지 파일 검사
  python scripts/check_public.py text < FILE    표준 입력(이슈, 댓글 본문) 검사
종료 코드 0이면 통과, 1이면 위반.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 50 * 1024 * 1024

# 금지 경로와 확장자
BLOCK_PATH = re.compile(r"^(private|reference)(/|$)|\.(docx|pdf|exe|zip)$", re.I)

# 문자열을 이어 붙여 이 파일 자체가 검사에 걸리지 않게 한다
def j(*parts):
    return "".join(parts)

# 어디에서도 금지(커밋 메시지, 이슈, 댓글, 파일 전부)
ALWAYS = [j("Co-", "Authored-", "By"), j("Generated ", "with"), j("AI-", "generated"), "HUMANIZE-SUMMARY", "_workspace"]
# 학습서 본문(courses/)에서는 기술 설명으로 허용, 그 밖에서는 금지
TOOLS = [j("Clau", "de"), j("Anthro", "pic"), j("Cod", "ex"), j("Chat", "GPT"), j("Open", "AI"), j("Co", "pilot"), j("G", "PT")]
# 목적 문구(어디에서도 금지)
PURPOSE = [j("면", "접"), j("자소", "서"), j("자기소개", "서"), j("DB ", "Inc"), j("채", "용"), j("입", "사")]

EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F2FF☀-⛿]")
MIDDOT = re.compile("[·・‧∙⋅•]")
BOLD_ITALIC = re.compile(r"\*\*|__|(?<![\w*])\*(?!\s)[^*\n]+?\*(?!\w)")


def strip_code(text):
    # 코드 블록과 인라인 코드는 표기 검사에서 뺀다
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def scan(text, where, allow_tools=False, markdown=False):
    errs = []
    words = ALWAYS + PURPOSE + ([] if allow_tools else TOOLS)
    for w in words:
        if w.lower() in text.lower():
            errs.append(f"{where}: 금지 문자열 '{w}'")
    if EMOJI.search(text):
        errs.append(f"{where}: 이모지")
    if MIDDOT.search(text):
        errs.append(f"{where}: 중앙점")
    if markdown and BOLD_ITALIC.search(strip_code(text)):
        errs.append(f"{where}: 굵게 또는 기울임 표기")
    return errs


def tracked_files():
    out = subprocess.run(["git", "ls-files", "--cached"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def check_files():
    errs = []
    for rel in tracked_files():
        if rel == "scripts/check_public.py":
            continue
        path = ROOT / rel
        if BLOCK_PATH.search(rel):
            errs.append(f"{rel}: 공개 금지 경로나 확장자")
            continue
        if not path.exists():
            continue
        if path.stat().st_size > MAX_BYTES:
            errs.append(f"{rel}: 50MB 초과")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        errs += scan(text, rel, allow_tools=rel.startswith("courses/"), markdown=rel.endswith(".md"))
    return errs


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "files"
    if mode == "files":
        errs = check_files()
    elif mode == "msg":
        text = Path(sys.argv[2]).read_text(encoding="utf-8")
        text = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
        errs = scan(text, "커밋 메시지")
    elif mode == "text":
        errs = scan(sys.stdin.read(), "본문", markdown=True)
    else:
        sys.exit("알 수 없는 모드: " + mode)
    for e in errs:
        print(e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
