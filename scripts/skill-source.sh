#!/usr/bin/env bash
# Resolve / persist "Skill 来源" for the current runtime environment.
# Never prints NOTION_API_KEY or other secrets.
#
# Usage:
#   skill-source.sh env          # print: cursor | hermes
#   skill-source.sh config-path # print path to skillfy.env for this env
#   skill-source.sh get         # print SKILL_SOURCE or MISSING
#   skill-source.sh set <name>  # persist SKILL_SOURCE (+ ensure Notion select option)
#   skill-source.sh list        # print JSON array of Notion "Skill 来源" options

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_ID="332a603bc24180398df7f9cdbba1fc2c"
NOTION_VERSION="2022-06-28"

detect_env() {
  if [[ -n "${SKILLFY_ENV:-}" ]]; then
    echo "$SKILLFY_ENV"
    return 0
  fi
  if [[ -n "${CURSOR_TRACE_ID:-}" || -n "${CURSOR_AGENT:-}" ]]; then
    echo "cursor"
    return 0
  fi
  local cwd="${PWD:-}"
  if [[ "$cwd" == *"/.cursor/"* ]] || [[ -d "${cwd}/.cursor" ]]; then
    echo "cursor"
    return 0
  fi
  if [[ "$cwd" == *"/.hermes/"* ]]; then
    echo "hermes"
    return 0
  fi
  if [[ -d "$HOME/.cursor/skills" && ! -d "$HOME/.hermes/skills" ]]; then
    echo "cursor"
    return 0
  fi
  echo "hermes"
}

config_path() {
  case "$(detect_env)" in
    cursor) echo "$HOME/.cursor/skillfy.env" ;;
    hermes) echo "$HOME/.hermes/skillfy.env" ;;
    *) echo "$HOME/.hermes/skillfy.env" ;;
  esac
}

load_dotenv() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  set -a
  # shellcheck disable=SC1090
  source "$f"
  set +a
  return 0
}

load_notion_token() {
  local env_kind
  env_kind="$(detect_env)"
  NOTION_API_KEY=""
  if [[ "$env_kind" == "cursor" ]]; then
    load_dotenv "$HOME/.cursor/.env" 2>/dev/null || true
  fi
  if [[ -z "${NOTION_API_KEY:-}" ]]; then
    load_dotenv "$HOME/.hermes/.env" 2>/dev/null || true
  fi
  [[ -n "${NOTION_API_KEY:-}" ]] || {
    echo "ERROR: NOTION_API_KEY not found in ~/.cursor/.env or ~/.hermes/.env" >&2
    exit 3
  }
}

read_source() {
  local cfg
  cfg="$(config_path)"
  if [[ -f "$cfg" ]]; then
    # shellcheck disable=SC1090
    source "$cfg"
    if [[ -n "${SKILL_SOURCE:-}" ]]; then
      echo "$SKILL_SOURCE"
      return 0
    fi
  fi
  echo "MISSING"
}

write_source() {
  local name="$1"
  local cfg dir
  cfg="$(config_path)"
  dir="$(dirname "$cfg")"
  mkdir -p "$dir"
  chmod 700 "$dir" 2>/dev/null || true
  if [[ -f "$cfg" ]] && grep -q '^SKILL_SOURCE=' "$cfg"; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s/^SKILL_SOURCE=.*/SKILL_SOURCE=${name}/" "$cfg"
    else
      sed -i "s/^SKILL_SOURCE=.*/SKILL_SOURCE=${name}/" "$cfg"
    fi
  else
    printf 'SKILL_SOURCE=%s\n' "$name" >>"$cfg"
  fi
  chmod 600 "$cfg" 2>/dev/null || true
}

ensure_notion_option() {
  local name="$1"
  load_notion_token
  command -v jq >/dev/null 2>&1 || {
    echo "ERROR: jq required (brew install jq)" >&2
    exit 5
  }
  local hdr_file db opts has
  hdr_file="$(mktemp)"
  chmod 600 "$hdr_file"
  printf 'Authorization: Bearer %s\nContent-Type: application/json\nNotion-Version: %s\n' \
    "$NOTION_API_KEY" "$NOTION_VERSION" >"$hdr_file"

  db="$(curl -sS -H @"$hdr_file" "https://api.notion.com/v1/databases/${DB_ID}")"
  rm -f "$hdr_file"
  has="$(echo "$db" | jq -r --arg n "$name" '
    .properties["Skill 来源"].select.options
    | map(.name) | index($n) // empty
  ')"
  if [[ -n "$has" ]]; then
    return 0
  fi
  opts="$(echo "$db" | jq --arg n "$name" '
    [.properties["Skill 来源"].select.options[]
     | {id, name, color: (.color // "default")}]
    + [{name: $n, color: "blue"}]
  ')"
  hdr_file="$(mktemp)"
  chmod 600 "$hdr_file"
  printf 'Authorization: Bearer %s\nContent-Type: application/json\nNotion-Version: %s\n' \
    "$NOTION_API_KEY" "$NOTION_VERSION" >"$hdr_file"
  curl -sS -X PATCH "https://api.notion.com/v1/databases/${DB_ID}" \
    -H @"$hdr_file" \
    -d "$(jq -n --argjson o "$opts" '{properties: {"Skill 来源": {select: {options: $o}}}}')" \
    >/dev/null
  rm -f "$hdr_file"
}

cmd_list() {
  load_notion_token
  command -v jq >/dev/null 2>&1 || { echo "ERROR: jq required" >&2; exit 5; }
  local hdr_file db
  hdr_file="$(mktemp)"
  chmod 600 "$hdr_file"
  printf 'Authorization: Bearer %s\nContent-Type: application/json\nNotion-Version: %s\n' \
    "$NOTION_API_KEY" "$NOTION_VERSION" >"$hdr_file"
  db="$(curl -sS -H @"$hdr_file" "https://api.notion.com/v1/databases/${DB_ID}")"
  rm -f "$hdr_file"
  echo "$db" | jq '[.properties["Skill 来源"].select.options[].name]'
}

sub="${1:-}"; shift || true
case "$sub" in
  env)          detect_env ;;
  config-path)  config_path ;;
  get)          read_source ;;
  set)
    name="${1:?usage: skill-source.sh set <Skill 来源名称>}"
    ensure_notion_option "$name"
    write_source "$name"
    echo "OK: SKILL_SOURCE=$name ($(detect_env) → $(config_path))"
    ;;
  list)         cmd_list ;;
  ""|-h|--help)
    sed -n '2,12p' "$0"
    ;;
  *) echo "Unknown: $sub" >&2; exit 1 ;;
esac
