#!/usr/bin/env python3
"""
Notion Skill 单条 upsert — 只处理当前 skill，不扫描全量。
如果 Notion 中已存在同名条目则更新，不存在则创建。
用法: python3 notion-upsert-single.py <skill-name>
"""

import json, urllib.request, os, sys, re, time

def main():
    if len(sys.argv) < 2:
        print("Usage: notion-upsert-single.py <skill-name>")
        sys.exit(1)
    skill_name = sys.argv[1]

    # Find skill path
    home = os.path.expanduser("~")
    skill_path = None
    for base in [os.path.join(home, ".hermes", "skills"), os.path.join(home, ".cursor", "skills")]:
        for root, dirs, files in os.walk(base):
            if os.path.basename(root) == skill_name and "SKILL.md" in files:
                skill_path = root
                break
        if skill_path:
            break
    if not skill_path:
        print(f"Error: Skill '{skill_name}' not found")
        sys.exit(1)

    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"Error: SKILL.md not found at {skill_md}")
        sys.exit(1)

    # Parse frontmatter
    with open(skill_md) as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        print(f"Error: No YAML frontmatter in {skill_md}")
        sys.exit(1)

    import yaml
    fm = yaml.safe_load(m.group(1))
    desc = (fm.get("description", "") or "")[:500]

    # Get git remote
    repo = ""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=skill_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            repo = result.stdout.strip()
    except Exception:
        pass
    if not repo:
        repo = f"https://github.com/mynameisi/{skill_name}"
    repo = re.sub(r'git@github\.com:', 'https://github.com/', repo)
    repo = re.sub(r'\.git$', '', repo)

    # Get creation time
    created_date = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(skill_md)))

    # Get skill source from env file
    skillfy_env = os.path.expanduser("~/.hermes/skillfy.env")
    skill_source = "macbookpro-cursor"
    if os.path.isfile(skillfy_env):
        with open(skillfy_env) as f:
            for line in f:
                if line.startswith("SKILL_SOURCE="):
                    skill_source = line.split("=", 1)[1].strip()
                    break

    # Read Notion API key
    env_path = os.path.expanduser("~/.hermes/.env")
    token = None
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("NOTION_API_KEY"):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not token:
        print("Error: NOTION_API_KEY not found in ~/.hermes/.env")
        sys.exit(1)

    DB_ID = "332a603bc24180398df7f9cdbba1fc2c"
    HEADERS = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    def notion_request(method, path, data=None):
        url = f"https://api.notion.com{path}"
        req_data = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=HEADERS, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Search existing entries
    existing_pages = {}
    req_data = json.dumps({"page_size": 100})
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{DB_ID}/query",
        data=req_data.encode("utf-8"),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for p in data.get("results", []):
        name = "".join(t.get("plain_text","") for t in p.get("properties",{}).get("Skill Name",{}).get("title",[]))
        if name:
            existing_pages[name] = p["id"]

    # Triggers — derive from skill name
    triggers = [skill_name.replace("-", " "), skill_name]

    props = {
        "Skill Name": {"title": [{"text": {"content": skill_name}}]},
        "Skill 创建时间": {"date": {"start": created_date}},
        "Skill 功能": {"rich_text": [{"text": {"content": desc}}]},
        "触发词": {"multi_select": [{"name": t} for t in triggers]},
        "Skill 来源": {"select": {"name": skill_source}},
        "Skill Git repo 地址": {"url": repo},
    }

    if skill_name in existing_pages:
        page_id = existing_pages[skill_name]
        notion_request("PATCH", f"/v1/pages/{page_id}", {"properties": props})
        print(f"Notion update: {skill_name}")
    else:
        payload = {"parent": {"database_id": DB_ID}, "properties": props}
        notion_request("POST", "/v1/pages", payload)
        print(f"Notion create: {skill_name}")

if __name__ == "__main__":
    main()
