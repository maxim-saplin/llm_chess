#!/usr/bin/env bash
set -euo pipefail

DEFAULT_SERVER_CMD="${MCP_SERVER_CMD:-npx -y chrome-devtools-mcp@latest --isolated}"
WAIT_FOR_VERBOSE="${WAIT_FOR_VERBOSE:-0}"

usage() {
  cat <<'EOF'
Usage:
  browser-session.sh session-list
  browser-session.sh ensure-session [session-name] [server-cmd]
  browser-session.sh start-session [session-name] [server-cmd]
  browser-session.sh stop-session [session-name]
  browser-session.sh navigate [session-name] <url> [timeout-ms]
  browser-session.sh snapshot [session-name] [--verbose]
  browser-session.sh click-selector [session-name] <css-selector> [--dbl-click]
  browser-session.sh fill-selector [session-name] <css-selector> <value>
  browser-session.sh get-selector-text [session-name] <css-selector>
  browser-session.sh assert-selector-contains [session-name] <css-selector> <needle>
  browser-session.sh wait-for-text [session-name] <text> [timeout-ms]
  browser-session.sh eval [session-name] <js-function> [arg ...]

  browser-session.sh console-list [session-name] [--types-json <json-array>] [--page-size <n>] [--include-preserved]
  browser-session.sh console-errors [session-name] [page-size] [--include-preserved]
  browser-session.sh console-message [session-name] <msgid>

  browser-session.sh network-list [session-name] [--resource-types-json <json-array>] [--page-size <n>] [--include-preserved]
  browser-session.sh network-failures [session-name] [page-size] [--include-preserved]
  browser-session.sh network-request [session-name] <reqid>

  browser-session.sh lighthouse [session-name] [mode] [device] [output-dir]
  browser-session.sh trace-start [session-name] [performance-start-trace args...]
  browser-session.sh trace-stop [session-name]
  browser-session.sh trace-insight [session-name] <insight-set-id> <insight-name>

  browser-session.sh tools-list [--session <session-name>] [pattern]
  browser-session.sh tool-help [--session <session-name>] <tool-name>
  browser-session.sh run-tool [--session <session-name>] <tool-name> [arg ...]

Defaults:
  session-name: browser
  server-cmd:   MCP_SERVER_CMD or npx -y chrome-devtools-mcp@latest --isolated
  lighthouse mode/device: snapshot desktop

Environment:
  MCP_SERVER_CMD   default server command for ensure/start session
  WAIT_FOR_VERBOSE if set to 1, wait-for-text prints full wait output
EOF
}

json_array() {
  node -e 'process.stdout.write(JSON.stringify(process.argv.slice(1)))' "$@"
}

json_string() {
  node -e 'process.stdout.write(JSON.stringify(process.argv[1]))' "$1"
}

is_tool_error_output() {
  local output="$1"
  local first_line="${output%%$'\n'*}"
  [[ "$first_line" == Error:* || "$first_line" == Unable\ to* ]]
}

run_mcp2cli() {
  local output
  if ! output="$(uvx mcp2cli "$@" 2>&1)"; then
    printf '%s\n' "$output" >&2
    return 1
  fi

  if is_tool_error_output "$output"; then
    printf '%s\n' "$output" >&2
    return 1
  fi

  printf '%s\n' "$output"
}

session_exists() {
  local session="$1"
  uvx mcp2cli --session-list 2>/dev/null | awk -v name="$session" '
    $1 == name && $0 ~ /(^|[[:space:]])alive([[:space:]]|$)/ { found = 1 }
    END { exit(found ? 0 : 1) }
  '
}

ensure_session() {
  local session="$1"
  local server_cmd="$2"
  if session_exists "$session"; then
    echo "SESSION REUSE: '$session' is already alive"
    return 0
  fi
  run_mcp2cli --session-start "$session" --mcp-stdio "$server_cmd"
}

start_session() {
  local session="$1"
  local server_cmd="$2"
  run_mcp2cli --session-start "$session" --mcp-stdio "$server_cmd"
}

run_eval() {
  local session="$1"
  local function="$2"
  shift 2

  local args_json='[]'
  if (($# > 0)); then
    args_json="$(json_array "$@")"
  fi

  local wrapper
  wrapper=$(cat <<EOF
() => {
  const __args = $args_json;
  return (${function})(...__args);
}
EOF
)

  run_mcp2cli --session "$session" evaluate-script --function "$wrapper"
}

run_wait_for_text() {
  local session="$1"
  local text="$2"
  local timeout_ms="$3"
  local texts_json
  texts_json="$(json_array "$text")"

  local output
  if ! output="$(uvx mcp2cli --session "$session" wait-for --text "$texts_json" --timeout "$timeout_ms" 2>&1)"; then
    printf '%s\n' "$output" >&2
    return 1
  fi

  if is_tool_error_output "$output"; then
    printf '%s\n' "${output%%$'\n'*}" >&2
    return 1
  fi

  if [[ "$WAIT_FOR_VERBOSE" == "1" ]]; then
    printf '%s\n' "$output"
  else
    printf '%s\n' "${output%%$'\n'*}"
  fi
}

case "${1:-}" in
  -h|--help|"")
    usage
    exit 0
    ;;
  session-list)
    run_mcp2cli --session-list
    ;;
  ensure-session)
    shift
    ensure_session "${1:-browser}" "${2:-$DEFAULT_SERVER_CMD}"
    ;;
  start-session)
    shift
    start_session "${1:-browser}" "${2:-$DEFAULT_SERVER_CMD}"
    ;;
  stop-session)
    shift
    run_mcp2cli --session-stop "${1:-browser}"
    ;;
  navigate)
    shift
    session="${1:-browser}"
    if [[ $# -lt 2 ]]; then
      usage
      exit 1
    fi
    url="$2"
    timeout_ms="${3:-60000}"
    run_mcp2cli --session "$session" navigate-page --url "$url" --timeout "$timeout_ms"
    ;;
  snapshot)
    shift
    session="${1:-browser}"
    if [[ "${2:-}" == "--verbose" ]]; then
      run_mcp2cli --session "$session" take-snapshot --verbose
    else
      run_mcp2cli --session "$session" take-snapshot
    fi
    ;;
  click-selector)
    shift
    session="${1:-browser}"
    if [[ $# -lt 2 ]]; then
      usage
      exit 1
    fi
    selector_json="$(json_string "$2")"
    dbl_click="false"
    if [[ "${3:-}" == "--dbl-click" ]]; then
      dbl_click="true"
    fi
    fn=$(cat <<EOF
() => {
  const selector = $selector_json;
  const dblClick = $dbl_click;
  const el = document.querySelector(selector);
  if (!el) {
    throw new Error("Selector not found: " + selector);
  }
  if (dblClick) {
    el.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
  } else {
    el.click();
  }
  return { ok: true, selector, dblClick };
}
EOF
)
    run_mcp2cli --session "$session" evaluate-script --function "$fn"
    ;;
  fill-selector)
    shift
    session="${1:-browser}"
    if [[ $# -lt 3 ]]; then
      usage
      exit 1
    fi
    selector_json="$(json_string "$2")"
    value_json="$(json_string "$3")"
    fn=$(cat <<EOF
() => {
  const selector = $selector_json;
  const value = $value_json;
  const el = document.querySelector(selector);
  if (!el) {
    throw new Error("Selector not found: " + selector);
  }

  const tag = (el.tagName || "").toLowerCase();
  const type = String(el.type || "").toLowerCase();
  const dispatch = (node) => {
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
  };
  const setNativeValue = (node, nextValue) => {
    const proto = node instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && typeof desc.set === "function") {
      desc.set.call(node, nextValue);
    } else {
      node.value = nextValue;
    }
    dispatch(node);
  };

  if (tag === "select") {
    el.value = value;
    dispatch(el);
    return { ok: true, selector, value };
  }

  if (type === "checkbox") {
    const on = ["1", "true", "yes", "on", "checked"].includes(String(value).toLowerCase());
    if (el.checked !== on) {
      el.click();
    } else {
      dispatch(el);
    }
    return { ok: true, selector, value: on };
  }

  if (type === "radio") {
    const on = ["1", "true", "yes", "on", "checked"].includes(String(value).toLowerCase());
    if (on && !el.checked) {
      el.click();
    }
    return { ok: true, selector, value: on };
  }

  if ("value" in el) {
    setNativeValue(el, value);
    return { ok: true, selector, value };
  }

  if (el.isContentEditable) {
    el.focus();
    el.textContent = value;
    dispatch(el);
    return { ok: true, selector, value };
  }

  el.textContent = value;
  return { ok: true, selector, value };
}
EOF
)
    run_mcp2cli --session "$session" evaluate-script --function "$fn"
    ;;
  get-selector-text)
    shift
    session="${1:-browser}"
    if [[ $# -lt 2 ]]; then
      usage
      exit 1
    fi
    selector_json="$(json_string "$2")"
    fn=$(cat <<EOF
() => {
  const selector = $selector_json;
  const el = document.querySelector(selector);
  if (!el) {
    throw new Error("Selector not found: " + selector);
  }
  return (el.innerText || el.textContent || "").trim();
}
EOF
)
    run_mcp2cli --session "$session" evaluate-script --function "$fn"
    ;;
  assert-selector-contains)
    shift
    session="${1:-browser}"
    if [[ $# -lt 3 ]]; then
      usage
      exit 1
    fi
    selector_json="$(json_string "$2")"
    needle_json="$(json_string "$3")"
    fn=$(cat <<EOF
() => {
  const selector = $selector_json;
  const needle = $needle_json;
  const el = document.querySelector(selector);
  if (!el) {
    throw new Error("Selector not found: " + selector);
  }
  const actual = (el.innerText || el.textContent || "").trim();
  if (!actual.includes(needle)) {
    throw new Error("Expected " + selector + " to contain " + JSON.stringify(needle) + ", got " + JSON.stringify(actual));
  }
  return { ok: true, selector, needle, actual };
}
EOF
)
    run_mcp2cli --session "$session" evaluate-script --function "$fn"
    ;;
  wait-for-text)
    shift
    session="${1:-browser}"
    if [[ $# -lt 2 ]]; then
      usage
      exit 1
    fi
    text="$2"
    timeout_ms="${3:-0}"
    run_wait_for_text "$session" "$text" "$timeout_ms"
    ;;
  eval)
    shift
    session="${1:-browser}"
    if [[ $# -lt 2 ]]; then
      usage
      exit 1
    fi
    function="$2"
    shift 2
    run_eval "$session" "$function" "$@"
    ;;
  console-list)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" ]]; then
      session="$1"
      shift
    fi

    types_json=""
    page_size=""
    include_preserved="false"

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --types-json)
          if [[ $# -lt 2 ]]; then
            usage
            exit 1
          fi
          types_json="$2"
          shift 2
          ;;
        --page-size)
          if [[ $# -lt 2 ]]; then
            usage
            exit 1
          fi
          page_size="$2"
          shift 2
          ;;
        --include-preserved)
          include_preserved="true"
          shift
          ;;
        *)
          usage
          exit 1
          ;;
      esac
    done

    args=(--session "$session" list-console-messages)
    if [[ -n "$types_json" ]]; then
      args+=(--types "$types_json")
    fi
    if [[ -n "$page_size" ]]; then
      args+=(--page-size "$page_size")
    fi
    if [[ "$include_preserved" == "true" ]]; then
      args+=(--include-preserved-messages)
    fi

    run_mcp2cli "${args[@]}"
    ;;
  console-errors)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" && ! "$1" =~ ^[0-9]+$ ]]; then
      session="$1"
      shift
    fi

    page_size="50"
    if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
      page_size="$1"
      shift
    fi

    include_preserved="false"
    if [[ "${1:-}" == "--include-preserved" ]]; then
      include_preserved="true"
      shift
    fi

    if [[ $# -ne 0 ]]; then
      usage
      exit 1
    fi

    args=(--session "$session" list-console-messages --types '["error"]' --page-size "$page_size")
    if [[ "$include_preserved" == "true" ]]; then
      args+=(--include-preserved-messages)
    fi

    run_mcp2cli "${args[@]}"
    ;;
  console-message)
    shift
    if [[ $# -eq 1 ]]; then
      session="browser"
      msgid="$1"
    elif [[ $# -eq 2 ]]; then
      session="$1"
      msgid="$2"
    else
      usage
      exit 1
    fi

    run_mcp2cli --session "$session" get-console-message --msgid "$msgid"
    ;;
  network-list)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" ]]; then
      session="$1"
      shift
    fi

    resource_types_json=""
    page_size=""
    include_preserved="false"

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --resource-types-json)
          if [[ $# -lt 2 ]]; then
            usage
            exit 1
          fi
          resource_types_json="$2"
          shift 2
          ;;
        --page-size)
          if [[ $# -lt 2 ]]; then
            usage
            exit 1
          fi
          page_size="$2"
          shift 2
          ;;
        --include-preserved)
          include_preserved="true"
          shift
          ;;
        *)
          usage
          exit 1
          ;;
      esac
    done

    args=(--session "$session" list-network-requests)
    if [[ -n "$resource_types_json" ]]; then
      args+=(--resource-types "$resource_types_json")
    fi
    if [[ -n "$page_size" ]]; then
      args+=(--page-size "$page_size")
    fi
    if [[ "$include_preserved" == "true" ]]; then
      args+=(--include-preserved-requests)
    fi

    run_mcp2cli "${args[@]}"
    ;;
  network-failures)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" && ! "$1" =~ ^[0-9]+$ ]]; then
      session="$1"
      shift
    fi

    page_size="200"
    if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
      page_size="$1"
      shift
    fi

    include_preserved="false"
    if [[ "${1:-}" == "--include-preserved" ]]; then
      include_preserved="true"
      shift
    fi

    if [[ $# -ne 0 ]]; then
      usage
      exit 1
    fi

    args=(--session "$session" list-network-requests --page-size "$page_size")
    if [[ "$include_preserved" == "true" ]]; then
      args+=(--include-preserved-requests)
    fi

    network_output="$(run_mcp2cli "${args[@]}")"
    failures="$(printf '%s\n' "$network_output" | awk '
      /^reqid=/ {
        if ($0 ~ /\[[0-9][0-9][0-9]\]$/) {
          code = substr($0, length($0) - 3, 3) + 0
          if (code >= 400 || code == 0) {
            print
          }
        } else {
          print
        }
      }
    ')"

    echo "## Failed network requests"
    if [[ -z "$failures" ]]; then
      echo "<no failed network requests found>"
    else
      printf '%s\n' "$failures"
    fi
    ;;
  network-request)
    shift
    if [[ $# -eq 1 ]]; then
      session="browser"
      reqid="$1"
    elif [[ $# -eq 2 ]]; then
      session="$1"
      reqid="$2"
    else
      usage
      exit 1
    fi

    run_mcp2cli --session "$session" get-network-request --reqid "$reqid"
    ;;
  lighthouse)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" && "$1" != "navigation" && "$1" != "snapshot" && "$1" != "desktop" && "$1" != "mobile" ]]; then
      session="$1"
      shift
    fi

    mode="snapshot"
    device="desktop"
    output_dir=""

    if [[ $# -gt 0 ]]; then
      mode="$1"
      shift
    fi
    if [[ $# -gt 0 ]]; then
      device="$1"
      shift
    fi
    if [[ $# -gt 0 ]]; then
      output_dir="$1"
      shift
    fi
    if [[ $# -ne 0 ]]; then
      usage
      exit 1
    fi

    args=(--session "$session" lighthouse-audit --mode "$mode" --device "$device")
    if [[ -n "$output_dir" ]]; then
      args+=(--output-dir-path "$output_dir")
    fi

    run_mcp2cli "${args[@]}"
    ;;
  trace-start)
    shift
    session="browser"
    if [[ $# -gt 0 && "${1:0:1}" != "-" ]]; then
      session="$1"
      shift
    fi

    run_mcp2cli --session "$session" performance-start-trace "$@"
    ;;
  trace-stop)
    shift
    session="${1:-browser}"
    if [[ $# -gt 1 ]]; then
      usage
      exit 1
    fi

    run_mcp2cli --session "$session" performance-stop-trace
    ;;
  trace-insight)
    shift
    if [[ $# -eq 2 ]]; then
      session="browser"
      insight_set_id="$1"
      insight_name="$2"
    elif [[ $# -eq 3 ]]; then
      session="$1"
      insight_set_id="$2"
      insight_name="$3"
    else
      usage
      exit 1
    fi

    run_mcp2cli --session "$session" performance-analyze-insight --insight-set-id "$insight_set_id" --insight-name "$insight_name"
    ;;
  tools-list)
    shift
    session="browser"
    if [[ "${1:-}" == "--session" ]]; then
      if [[ $# -lt 2 ]]; then
        usage
        exit 1
      fi
      session="$2"
      shift 2
    fi

    if [[ $# -gt 1 ]]; then
      usage
      exit 1
    fi

    if [[ $# -eq 1 ]]; then
      run_mcp2cli --session "$session" --search "$1" --compact
    else
      run_mcp2cli --session "$session" --list --compact
    fi
    ;;
  tool-help)
    shift
    session="browser"
    if [[ "${1:-}" == "--session" ]]; then
      if [[ $# -lt 3 ]]; then
        usage
        exit 1
      fi
      session="$2"
      shift 2
    fi

    if [[ $# -ne 1 ]]; then
      usage
      exit 1
    fi

    run_mcp2cli --session "$session" "$1" --help
    ;;
  run-tool)
    shift
    session="browser"
    if [[ "${1:-}" == "--session" ]]; then
      if [[ $# -lt 3 ]]; then
        usage
        exit 1
      fi
      session="$2"
      shift 2
    fi

    if [[ $# -lt 1 ]]; then
      usage
      exit 1
    fi

    tool="$1"
    shift
    run_mcp2cli --session "$session" "$tool" "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
