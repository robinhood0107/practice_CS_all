"""공개 저장소의 이슈와 댓글을 private/backup/issues.json으로 내려받는다(로컬 실행).

사용법: python scripts/backup_issues.py
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "private" / "backup" / "issues.json"


def gh_json(*args):
    return json.loads(subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8").stdout)


def main():
    issues = gh_json("issue", "list", "--state", "all", "--limit", "1000", "--json", "number,title,state,body,labels,createdAt,closedAt")
    for it in issues:
        it["comments"] = gh_json("issue", "view", str(it["number"]), "--json", "comments")["comments"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")
    print("백업:", len(issues), "개 이슈 →", OUT)


if __name__ == "__main__":
    main()
