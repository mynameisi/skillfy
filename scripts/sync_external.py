#!/usr/bin/env python3
"""Full sync user-built skills to Notion and/or Feishu Skill databases."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

NOTION_DB = os.environ.get("NOTION_DB_ID", "332a603bc24180398df7f9cdbba1fc2c")
NOTION_VER = "2022-06-28"
GITHUB_ORG = os.environ.get("GITHUB_ORG", "mynameisi")
FEISHU_ENV = Path(os.environ.expanduser(os.environ.get("FEISHU_SKILL_DB_ENV", "~/.cursor/feishu-skill-db.env")))
SKILLFY_ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_NAMES = {
    "create-skill", "create-rule", "create-hook", "update-cursor-settings",
    "canvas", "loop", "sdk", "split-to-prs", "babysit", "statusline",
}


@dataclass
class SkillRecord:
    name: str
    description: str
    created_date: str  # YYYY-MM-DD
    created_ms: int
    repo_url: str
    triggers: list[str]
    source: str
    path: str


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def skill_source() -> str:
    script = SKILLFY_ROOT / "scripts" / "skill-source.sh"
    r = subprocess.run(["bash", str(script), "get"], capture_output=True, text=True)
    v = (r.stdout or "").strip()
    if v == "MISSING":
        print("ERROR: SKILL_SOURCE missing — run skillfy step 0 first", file=sys.stderr)
        sys.exit(3)
    return v


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def infer_triggers(desc: str, name: str) -> list[str]:
    words = set()
    for w in re.findall(r"[A-Za-z]{3,}", desc + " " + name):
        words.add(w.lower())
    for zh in re.findall(r"[\u4e00-\u9fff]{2,}", desc + " " + name):
        if len(zh) <= 8:
            words.add(zh)
    # cap and prefer short trigger-like tokens
    picks = []
    for hint in ("skill", "grafana", "dashboard", "notion", "feishu", "git", "sync"):
        if hint in words or hint in name.lower():
            picks.append(hint.capitalize() if hint == "grafana" else hint)
    for w in sorted(words)[:5]:
        if w not in picks and len(picks) < 7:
            picks.append(w)
    return picks[:7] or ["skill"]


def git_repo_url(skill_dir: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", str(skill_dir), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    if GITHUB_ORG not in url:
        return None
    m = re.search(rf"github\.com[:/]+{re.escape(GITHUB_ORG)}/([^/\s#?]+)", url)
    if not m:
        return None
    repo = m.group(1).replace(".git", "")
    return f"https://github.com/{GITHUB_ORG}/{repo}"


def repo_name_from_url(url: str) -> str:
    m = re.search(r"github\.com/[^/]+/([^/\s#?]+)", url)
    return m.group(1).replace(".git", "") if m else ""


def discover_skills(extra_roots: list[Path] | None = None) -> list[SkillRecord]:
    roots = [
        Path.home() / ".hermes" / "skills",
        Path.home() / ".cursor" / "skills",
    ]
    if extra_roots:
        roots.extend(extra_roots)
    seen: dict[str, SkillRecord] = {}
    source = skill_source()

    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in root.rglob("SKILL.md"):
            parts = skill_md.parts
            if len(parts) < 3:
                continue
            dir_name = parts[-2]
            if dir_name in EXCLUDE_NAMES or dir_name.startswith("."):
                continue
            skill_dir = skill_md.parent
            url = git_repo_url(skill_dir)
            if not url:
                continue
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
            desc = fm.get("description") or fm.get("name") or dir_name
            if len(desc) < 10:
                continue
            mtime = skill_md.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc).astimezone()
            created_date = dt.strftime("%Y-%m-%d")
            created_ms = int(dt.timestamp() * 1000)
            name = repo_name_from_url(url) or fm.get("name") or dir_name
            rec = SkillRecord(
                name=name,
                description=desc[:2000],
                created_date=created_date,
                created_ms=created_ms,
                repo_url=url,
                triggers=infer_triggers(desc, name),
                source=source,
                path=str(skill_dir),
            )
            # prefer entry with real github remote over duplicate dir names
            seen[name] = rec
    return sorted(seen.values(), key=lambda r: r.name)


def notion_request(token: str, method: str, path: str, body: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VER,
    }
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    req = urllib.request.Request(f"https://api.notion.com{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def notion_query_all(token: str) -> dict[str, str]:
    """name -> page_id"""
    existing: dict[str, str] = {}
    cursor = None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion_request(token, "POST", f"/v1/databases/{NOTION_DB}/query", body)
        for p in data.get("results", []):
            title = "".join(
                t.get("plain_text", "")
                for t in p.get("properties", {}).get("Skill Name", {}).get("title", [])
            )
            if title:
                existing[title] = p["id"]
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return existing


def notion_upsert(token: str, rec: SkillRecord, existing: dict[str, str]) -> str:
    props = {
        "Skill Name": {"title": [{"text": {"content": rec.name}}]},
        "Skill 创建时间": {"date": {"start": rec.created_date}},
        "Skill 功能": {"rich_text": [{"text": {"content": rec.description[:2000]}}]},
        "触发词": {"multi_select": [{"name": t} for t in rec.triggers]},
        "Skill 来源": {"select": {"name": rec.source}},
        "Skill Git repo 地址": {"url": rec.repo_url},
    }
    if rec.name in existing:
        notion_request(token, "PATCH", f"/v1/pages/{existing[rec.name]}", {"properties": props})
        return "updated"
    notion_request(
        token,
        "POST",
        "/v1/pages",
        {"parent": {"database_id": NOTION_DB}, "properties": props},
    )
    return "created"


def sync_notion(records: list[SkillRecord]) -> None:
    env = load_env(Path.home() / ".hermes" / ".env")
    token = env.get("NOTION_API_KEY", "")
    if not token:
        print("SKIP notion: NOTION_API_KEY not in ~/.hermes/.env", file=sys.stderr)
        return
    existing = notion_query_all(token)
    for rec in records:
        try:
            action = notion_upsert(token, rec, existing)
            print(f"  notion {action}: {rec.name}")
            if action == "created":
                existing[rec.name] = "new"
        except urllib.error.HTTPError as e:
            print(f"  notion FAIL {rec.name}: {e.code} {e.read().decode()[:200]}", file=sys.stderr)


def lark_json(cmd: list[str], body: dict | None = None) -> dict:
    lark = os.environ.get(
        "LARK_CLI", str(Path.home() / ".nvm/versions/node/v22.22.3/bin/lark-cli")
    )
    full = [lark, "--as", "user"] + cmd
    if body is not None:
        full += ["--json", json.dumps(body, ensure_ascii=False)]
    r = subprocess.run(full, capture_output=True, text=True, env={**os.environ, "HERMES_HOME": os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))})
    if not r.stdout.strip():
        raise RuntimeError(r.stderr[:400])
    return json.loads(r.stdout)


def feishu_load() -> tuple[str, str]:
    if not FEISHU_ENV.exists():
        print("SKIP feishu: missing", FEISHU_ENV, file=sys.stderr)
        return "", ""
    env = load_env(FEISHU_ENV)
    return env.get("BASE_TOKEN", ""), env.get("TABLE_ID", "")


def feishu_existing_names(base: str, tbl: str) -> set[str]:
    data = lark_json(["base", "+record-list", "--base-token", base, "--table-id", tbl, "--format", "json", "--limit", "200"])
    fields = data["data"]["fields"]
    names = set()
    for row in data["data"]["data"]:
        d = dict(zip(fields, row))
        n = d.get("Skill Name")
        if n:
            names.add(str(n).strip())
    return names


def feishu_upsert(base: str, tbl: str, rec: SkillRecord, existing: set[str]) -> None:
    if rec.name in existing:
        print(f"  feishu skip (exists): {rec.name}")
        return
    # use only triggers that are likely in field — script may have added skill, etc.
    trig = [t for t in rec.triggers if len(t) <= 20][:7] or ["skill"]
    payload = {
        "fields": ["Skill Name", "Skill 创建时间", "触发词", "Skill 来源", "Skill 功能", "Skill Git repo 地址"],
        "rows": [[rec.name, rec.created_ms, trig, rec.source, rec.description, rec.repo_url]],
    }
    try:
        resp = lark_json(["base", "+record-batch-create", "--base-token", base, "--table-id", tbl], payload)
        if resp.get("ok"):
            print(f"  feishu created: {rec.name}")
            existing.add(rec.name)
        else:
            print(f"  feishu FAIL {rec.name}: {resp.get('error')}", file=sys.stderr)
    except Exception as e:
        print(f"  feishu FAIL {rec.name}: {e}", file=sys.stderr)


def sync_feishu(records: list[SkillRecord]) -> None:
    base, tbl = feishu_load()
    if not base or not tbl:
        return
    st = subprocess.run(
        [os.environ.get("LARK_CLI", ""), "auth", "status"],
        capture_output=True,
        text=True,
        env=os.environ,
    )
    if not st.stdout or "user" not in st.stdout or '"available": true' not in st.stdout.replace(" ", ""):
        # loose check
        try:
            j = json.loads(st.stdout)
            if not j.get("identities", {}).get("user", {}).get("available"):
                print("SKIP feishu: lark-cli user not ready", file=sys.stderr)
                return
        except json.JSONDecodeError:
            print("SKIP feishu: lark-cli auth check failed", file=sys.stderr)
            return
    existing = feishu_existing_names(base, tbl)
    for i, rec in enumerate(records):
        if i:
            time.sleep(2.0)
        feishu_upsert(base, tbl, rec, existing)


def cmd_check() -> None:
    ok_n = bool(load_env(Path.home() / ".hermes" / ".env").get("NOTION_API_KEY"))
    ok_f = FEISHU_ENV.exists()
    print(f"notion: {'OK' if ok_n else 'MISSING NOTION_API_KEY'}")
    print(f"feishu: {'OK' if ok_f else 'MISSING'} {FEISHU_ENV}")
    try:
        print(f"skill_source: {skill_source()}")
    except SystemExit:
        pass


def cmd_sync(target: str, extra: list[str]) -> None:
    extra_roots = [Path(p) for p in extra if p]
    records = discover_skills(extra_roots)
    print(f"Discovered {len(records)} skills with github.com/{GITHUB_ORG}/ remotes")
    for r in records:
        print(f"  - {r.name} ({r.path})")
    if target in ("notion", "all"):
        print("\n== Notion full sync ==")
        sync_notion(records)
    if target in ("feishu", "all"):
        print("\n== Feishu full sync ==")
        sync_feishu(records)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: sync_external.py check | sync --target notion|feishu|all [extra_skill_roots...]")
        sys.exit(1)
    if sys.argv[1] == "check":
        cmd_check()
        return
    if sys.argv[1] == "sync":
        target = "all"
        extra: list[str] = []
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--target" and i + 1 < len(args):
                target = args[i + 1]
                i += 2
            else:
                extra.append(args[i])
                i += 1
        cmd_sync(target, extra)
        return
    print("unknown command", file=sys.argv[1])
    sys.exit(1)


if __name__ == "__main__":
    main()
