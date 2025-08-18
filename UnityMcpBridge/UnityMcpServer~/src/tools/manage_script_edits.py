from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, List, Tuple
import base64
import re
from unity_connection import send_command_with_retry


def _apply_edits_locally(original_text: str, edits: List[Dict[str, Any]]) -> str:
    text = original_text
    for edit in edits or []:
        op = (
            (edit.get("op")
             or edit.get("operation")
             or edit.get("type")
             or edit.get("mode")
             or "")
            .strip()
            .lower()
        )

        if not op:
            allowed = "anchor_insert, prepend, append, replace_range, regex_replace"
            raise RuntimeError(
                f"op is required; allowed: {allowed}. Use 'op' (aliases accepted: type/mode/operation)."
            )

        if op == "prepend":
            prepend_text = edit.get("text", "")
            text = (prepend_text if prepend_text.endswith("\n") else prepend_text + "\n") + text
        elif op == "append":
            append_text = edit.get("text", "")
            if not text.endswith("\n"):
                text += "\n"
            text += append_text
            if not text.endswith("\n"):
                text += "\n"
        elif op == "anchor_insert":
            anchor = edit.get("anchor", "")
            position = (edit.get("position") or "before").lower()
            insert_text = edit.get("text", "")
            flags = re.MULTILINE
            m = re.search(anchor, text, flags)
            if not m:
                if edit.get("allow_noop", True):
                    continue
                raise RuntimeError(f"anchor not found: {anchor}")
            idx = m.start() if position == "before" else m.end()
            text = text[:idx] + insert_text + text[idx:]
        elif op == "replace_range":
            start_line = int(edit.get("startLine", 1))
            end_line = int(edit.get("endLine", start_line))
            replacement = edit.get("text", "")
            lines = text.splitlines(keepends=True)
            max_end = len(lines) + 1
            if start_line < 1 or end_line < start_line or end_line > max_end:
                raise RuntimeError("replace_range out of bounds")
            a = start_line - 1
            b = min(end_line, len(lines))
            rep = replacement
            if rep and not rep.endswith("\n"):
                rep += "\n"
            text = "".join(lines[:a]) + rep + "".join(lines[b:])
        elif op == "regex_replace":
            pattern = edit.get("pattern", "")
            repl = edit.get("replacement", "")
            count = int(edit.get("count", 0))  # 0 = replace all
            flags = re.MULTILINE
            if edit.get("ignore_case"):
                flags |= re.IGNORECASE
            text = re.sub(pattern, repl, text, count=count, flags=flags)
        else:
            allowed = "anchor_insert, prepend, append, replace_range, regex_replace"
            raise RuntimeError(f"unknown edit op: {op}; allowed: {allowed}. Use 'op' (aliases accepted: type/mode/operation).")
    return text


def _infer_class_name(script_name: str) -> str:
    # Default to script name as class name (common Unity pattern)
    return (script_name or "").strip()


def _extract_code_after(keyword: str, request: str) -> str:
    # Deprecated with NL removal; retained as no-op for compatibility
    idx = request.lower().find(keyword)
    if idx >= 0:
        return request[idx + len(keyword):].strip()
    return ""


def _normalize_script_locator(name: str, path: str) -> Tuple[str, str]:
    """Best-effort normalization of script "name" and "path".

    Accepts any of:
    - name = "SmartReach", path = "Assets/Scripts/Interaction"
    - name = "SmartReach.cs", path = "Assets/Scripts/Interaction"
    - name = "Assets/Scripts/Interaction/SmartReach.cs", path = ""
    - path = "Assets/Scripts/Interaction/SmartReach.cs" (name empty)
    - name or path using uri prefixes: unity://path/..., file://...
    - accidental duplicates like "Assets/.../SmartReach.cs/SmartReach.cs"

    Returns (name_without_extension, directory_path_under_Assets).
    """
    n = (name or "").strip()
    p = (path or "").strip()

    def strip_prefix(s: str) -> str:
        if s.startswith("unity://path/"):
            return s[len("unity://path/"):]
        if s.startswith("file://"):
            return s[len("file://"):]
        return s

    def collapse_duplicate_tail(s: str) -> str:
        # Collapse trailing "/X.cs/X.cs" to "/X.cs"
        parts = s.split("/")
        if len(parts) >= 2 and parts[-1] == parts[-2]:
            parts = parts[:-1]
        return "/".join(parts)

    # Prefer a full path if provided in either field
    candidate = ""
    for v in (n, p):
        v2 = strip_prefix(v)
        if v2.endswith(".cs") or v2.startswith("Assets/"):
            candidate = v2
            break

    if candidate:
        candidate = collapse_duplicate_tail(candidate)
        # If a directory was passed in path and file in name, join them
        if not candidate.endswith(".cs") and n.endswith(".cs"):
            v2 = strip_prefix(n)
            candidate = (candidate.rstrip("/") + "/" + v2.split("/")[-1])
        if candidate.endswith(".cs"):
            parts = candidate.split("/")
            file_name = parts[-1]
            dir_path = "/".join(parts[:-1]) if len(parts) > 1 else "Assets"
            base = file_name[:-3] if file_name.lower().endswith(".cs") else file_name
            return base, dir_path

    # Fall back: remove extension from name if present and return given path
    base_name = n[:-3] if n.lower().endswith(".cs") else n
    return base_name, (p or "Assets")


# Natural-language parsing removed; clients should send structured edits.


def register_manage_script_edits_tools(mcp: FastMCP):
    @mcp.tool(description=(
        "Apply targeted edits to an existing C# script (no full-file overwrite).\n\n"
        "Canonical fields (use these exact keys):\n"
        "- op: replace_method | insert_method | delete_method | anchor_insert | anchor_delete | anchor_replace\n"
        "- className: string (defaults to 'name' if omitted on method/class ops)\n"
        "- methodName: string (required for replace_method, delete_method)\n"
        "- replacement: string (required for replace_method, insert_method)\n"
        "- position: start | end | after | before (insert_method only)\n"
        "- afterMethodName / beforeMethodName: string (required when position='after'/'before')\n"
        "- anchor: regex string (for anchor_* ops)\n"
        "- text: string (for anchor_insert/anchor_replace)\n\n"
        "Do NOT use: new_method, anchor_method, content, newText (aliases accepted but normalized).\n\n"
        "Examples:\n"
        "1) Replace a method:\n"
        "{ 'name':'SmartReach','path':'Assets/Scripts/Interaction','edits':[\n"
        "  { 'op':'replace_method','className':'SmartReach','methodName':'HasTarget',\n"
        "    'replacement':'public bool HasTarget(){ return currentTarget!=null; }' }\n"
        "], 'options':{'validate':'standard','refresh':'immediate'} }\n\n"
        "2) Insert a method after another:\n"
        "{ 'name':'SmartReach','path':'Assets/Scripts/Interaction','edits':[\n"
        "  { 'op':'insert_method','className':'SmartReach','replacement':'public void PrintSeries(){ Debug.Log(seriesName); }',\n"
        "    'position':'after','afterMethodName':'GetCurrentTarget' }\n"
        "] }\n"
    ))
    def script_apply_edits(
        ctx: Context,
        name: str,
        path: str,
        edits: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        script_type: str = "MonoBehaviour",
        namespace: str = "",
    ) -> Dict[str, Any]:
        # Normalize locator first so downstream calls target the correct script file.
        name, path = _normalize_script_locator(name, path)

        # No NL path: clients must provide structured edits in 'edits'.

        # Normalize unsupported or aliased ops to known structured/text paths
        def _unwrap_and_alias(edit: Dict[str, Any]) -> Dict[str, Any]:
            # Unwrap single-key wrappers like {"replace_method": {...}}
            for wrapper_key in (
                "replace_method","insert_method","delete_method",
                "replace_class","delete_class",
                "anchor_insert","anchor_replace","anchor_delete",
            ):
                if wrapper_key in edit and isinstance(edit[wrapper_key], dict):
                    inner = dict(edit[wrapper_key])
                    inner["op"] = wrapper_key
                    edit = inner
                    break

            e = dict(edit)
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
            if op:
                e["op"] = op

            # Common field aliases
            if "class_name" in e and "className" not in e:
                e["className"] = e.pop("class_name")
            if "class" in e and "className" not in e:
                e["className"] = e.pop("class")
            if "method_name" in e and "methodName" not in e:
                e["methodName"] = e.pop("method_name")
            # Some clients use a generic 'target' for method name
            if "target" in e and "methodName" not in e:
                e["methodName"] = e.pop("target")
            if "method" in e and "methodName" not in e:
                e["methodName"] = e.pop("method")
            if "new_content" in e and "replacement" not in e:
                e["replacement"] = e.pop("new_content")
            if "newMethod" in e and "replacement" not in e:
                e["replacement"] = e.pop("newMethod")
            if "new_method" in e and "replacement" not in e:
                e["replacement"] = e.pop("new_method")
            if "content" in e and "replacement" not in e:
                e["replacement"] = e.pop("content")
            if "after" in e and "afterMethodName" not in e:
                e["afterMethodName"] = e.pop("after")
            if "after_method" in e and "afterMethodName" not in e:
                e["afterMethodName"] = e.pop("after_method")
            if "before" in e and "beforeMethodName" not in e:
                e["beforeMethodName"] = e.pop("before")
            if "before_method" in e and "beforeMethodName" not in e:
                e["beforeMethodName"] = e.pop("before_method")
            # anchor_method → before/after based on position (default after)
            if "anchor_method" in e:
                anchor = e.pop("anchor_method")
                pos = (e.get("position") or "after").strip().lower()
                if pos == "before" and "beforeMethodName" not in e:
                    e["beforeMethodName"] = anchor
                elif "afterMethodName" not in e:
                    e["afterMethodName"] = anchor
            if "anchorText" in e and "anchor" not in e:
                e["anchor"] = e.pop("anchorText")
            if "pattern" in e and "anchor" not in e and e.get("op") and e["op"].startswith("anchor_"):
                e["anchor"] = e.pop("pattern")
            if "newText" in e and "text" not in e:
                e["text"] = e.pop("newText")

            # LSP-like range edit -> replace_range
            if "range" in e and isinstance(e["range"], dict):
                rng = e.pop("range")
                start = rng.get("start", {})
                end = rng.get("end", {})
                # Convert 0-based to 1-based line/col
                e["op"] = "replace_range"
                e["startLine"] = int(start.get("line", 0)) + 1
                e["startCol"] = int(start.get("character", 0)) + 1
                e["endLine"] = int(end.get("line", 0)) + 1
                e["endCol"] = int(end.get("character", 0)) + 1
                if "newText" in edit and "text" not in e:
                    e["text"] = edit.get("newText", "")
            return e

        normalized_edits: List[Dict[str, Any]] = []
        for raw in edits or []:
            e = _unwrap_and_alias(raw)
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()

            # Default className to script name if missing on structured method/class ops
            if op in ("replace_class","delete_class","replace_method","delete_method","insert_method") and not e.get("className"):
                e["className"] = name

            # Map common aliases for text ops
            if op in ("text_replace",):
                e["op"] = "replace_range"
                normalized_edits.append(e)
                continue
            if op in ("regex_delete",):
                e["op"] = "regex_replace"
                e.setdefault("text", "")
                normalized_edits.append(e)
                continue
            if op == "regex_replace" and ("replacement" not in e):
                if "text" in e:
                    e["replacement"] = e.get("text", "")
                elif "insert" in e or "content" in e:
                    e["replacement"] = e.get("insert") or e.get("content") or ""
            if op == "anchor_insert" and not (e.get("text") or e.get("insert") or e.get("content") or e.get("replacement")):
                e["op"] = "anchor_delete"
                normalized_edits.append(e)
                continue
            normalized_edits.append(e)

        edits = normalized_edits
        normalized_for_echo = edits

        # Validate required fields and produce machine-parsable hints
        def error_with_hint(message: str, expected: Dict[str, Any], suggestion: Dict[str, Any]) -> Dict[str, Any]:
            return {"success": False, "message": message, "expected": expected, "rewrite_suggestion": suggestion}

        for e in edits or []:
            op = e.get("op", "")
            if op == "replace_method":
                if not e.get("methodName"):
                    return error_with_hint(
                        "replace_method requires 'methodName'.",
                        {"op": "replace_method", "required": ["className", "methodName", "replacement"]},
                        {"edits[0].methodName": "HasTarget"}
                    )
                if not (e.get("replacement") or e.get("text")):
                    return error_with_hint(
                        "replace_method requires 'replacement' (inline or base64).",
                        {"op": "replace_method", "required": ["className", "methodName", "replacement"]},
                        {"edits[0].replacement": "public bool X(){ return true; }"}
                    )
            elif op == "insert_method":
                if not (e.get("replacement") or e.get("text")):
                    return error_with_hint(
                        "insert_method requires a non-empty 'replacement'.",
                        {"op": "insert_method", "required": ["className", "replacement"], "position": {"after_requires": "afterMethodName", "before_requires": "beforeMethodName"}},
                        {"edits[0].replacement": "public void PrintSeries(){ Debug.Log(\"1,2,3\"); }"}
                    )
                pos = (e.get("position") or "").lower()
                if pos == "after" and not e.get("afterMethodName"):
                    return error_with_hint(
                        "insert_method with position='after' requires 'afterMethodName'.",
                        {"op": "insert_method", "position": {"after_requires": "afterMethodName"}},
                        {"edits[0].afterMethodName": "GetCurrentTarget"}
                    )
                if pos == "before" and not e.get("beforeMethodName"):
                    return error_with_hint(
                        "insert_method with position='before' requires 'beforeMethodName'.",
                        {"op": "insert_method", "position": {"before_requires": "beforeMethodName"}},
                        {"edits[0].beforeMethodName": "GetCurrentTarget"}
                    )
            elif op == "delete_method":
                if not e.get("methodName"):
                    return error_with_hint(
                        "delete_method requires 'methodName'.",
                        {"op": "delete_method", "required": ["className", "methodName"]},
                        {"edits[0].methodName": "PrintSeries"}
                    )
            elif op in ("anchor_insert", "anchor_replace", "anchor_delete"):
                if not e.get("anchor"):
                    return error_with_hint(
                        f"{op} requires 'anchor' (regex).",
                        {"op": op, "required": ["anchor"]},
                        {"edits[0].anchor": "(?m)^\\s*public\\s+bool\\s+HasTarget\\s*\\("}
                    )
                if op in ("anchor_insert", "anchor_replace") and not (e.get("text") or e.get("replacement")):
                    return error_with_hint(
                        f"{op} requires 'text'.",
                        {"op": op, "required": ["anchor", "text"]},
                        {"edits[0].text": "/* comment */\n"}
                    )

        for e in edits or []:
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
            if op in ("replace_class", "delete_class", "replace_method", "delete_method", "insert_method", "anchor_insert", "anchor_delete", "anchor_replace"):
                # Default applyMode to sequential if mixing insert + replace in the same batch
                ops_in_batch = { (x.get("op") or "").lower() for x in edits or [] }
                options = dict(options or {})
                if "insert_method" in ops_in_batch and "replace_method" in ops_in_batch and "applyMode" not in options:
                    options["applyMode"] = "sequential"

                params: Dict[str, Any] = {
                    "action": "edit",
                    "name": name,
                    "path": path,
                    "namespace": namespace,
                    "scriptType": script_type,
                    "edits": edits,
                }
                if options is not None:
                    params["options"] = options
                resp = send_command_with_retry("manage_script", params)
                if isinstance(resp, dict):
                    resp.setdefault("data", {})["normalizedEdits"] = normalized_for_echo
                return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}

        # 1) read from Unity
        read_resp = send_command_with_retry("manage_script", {
            "action": "read",
            "name": name,
            "path": path,
            "namespace": namespace,
            "scriptType": script_type,
        })
        if not isinstance(read_resp, dict) or not read_resp.get("success"):
            return read_resp if isinstance(read_resp, dict) else {"success": False, "message": str(read_resp)}

        data = read_resp.get("data") or read_resp.get("result", {}).get("data") or {}
        contents = data.get("contents")
        if contents is None and data.get("contentsEncoded") and data.get("encodedContents"):
            contents = base64.b64decode(data["encodedContents"]).decode("utf-8")
        if contents is None:
            return {"success": False, "message": "No contents returned from Unity read."}

        # Optional preview/dry-run: apply locally and return diff without writing
        preview = bool((options or {}).get("preview"))

        # If the edits are text-ops, prefer sending them to Unity's apply_text_edits with precondition
        # so header guards and validation run on the C# side.
        # Supported conversions: anchor_insert, replace_range, regex_replace (first match only).
        text_ops = { (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower() for e in (edits or []) }
        structured_kinds = {"replace_class","delete_class","replace_method","delete_method","insert_method","anchor_insert"}
        if not text_ops.issubset(structured_kinds):
            # Convert to apply_text_edits payload
            try:
                current_text = contents
                def line_col_from_index(idx: int) -> Tuple[int, int]:
                    # 1-based line/col
                    line = current_text.count("\n", 0, idx) + 1
                    last_nl = current_text.rfind("\n", 0, idx)
                    col = (idx - (last_nl + 1)) + 1 if last_nl >= 0 else idx + 1
                    return line, col

                at_edits: List[Dict[str, Any]] = []
                import re as _re
                for e in edits or []:
                    op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
                    # aliasing for text field
                    text_field = e.get("text") or e.get("insert") or e.get("content") or ""
                    if op == "anchor_insert":
                        anchor = e.get("anchor") or ""
                        position = (e.get("position") or "before").lower()
                        m = _re.search(anchor, current_text, _re.MULTILINE)
                        if not m:
                            return {"success": False, "message": f"anchor not found: {anchor}"}
                        idx = m.start() if position == "before" else m.end()
                        sl, sc = line_col_from_index(idx)
                        at_edits.append({
                            "startLine": sl,
                            "startCol": sc,
                            "endLine": sl,
                            "endCol": sc,
                            "newText": text_field or ""
                        })
                        # Update local snapshot to keep subsequent anchors stable
                        current_text = current_text[:idx] + (text_field or "") + current_text[idx:]
                    elif op == "replace_range":
                        # Directly forward if already in line/col form
                        if "startLine" in e:
                            at_edits.append({
                                "startLine": int(e.get("startLine", 1)),
                                "startCol": int(e.get("startCol", 1)),
                                "endLine": int(e.get("endLine", 1)),
                                "endCol": int(e.get("endCol", 1)),
                                "newText": text_field
                            })
                        else:
                            # If only indices provided, skip (we don't support index-based here)
                            return {"success": False, "message": "replace_range requires startLine/startCol/endLine/endCol"}
                    elif op == "regex_replace":
                        pattern = e.get("pattern") or ""
                        repl = text_field
                        m = _re.search(pattern, current_text, _re.MULTILINE)
                        if not m:
                            continue
                        sl, sc = line_col_from_index(m.start())
                        el, ec = line_col_from_index(m.end())
                        at_edits.append({
                            "startLine": sl,
                            "startCol": sc,
                            "endLine": el,
                            "endCol": ec,
                            "newText": repl
                        })
                        current_text = current_text[:m.start()] + repl + current_text[m.end():]
                    else:
                        return {"success": False, "message": f"Unsupported text edit op for server-side apply_text_edits: {op}"}

                if not at_edits:
                    return {"success": False, "message": "No applicable text edit spans computed (anchor not found or zero-length)."}

                # Send to Unity with precondition SHA to enforce guards and immediate refresh
                import hashlib
                sha = hashlib.sha256(contents.encode("utf-8")).hexdigest()
                params: Dict[str, Any] = {
                    "action": "apply_text_edits",
                    "name": name,
                    "path": path,
                    "namespace": namespace,
                    "scriptType": script_type,
                    "edits": at_edits,
                    "precondition_sha256": sha,
                    "options": {
                        "refresh": "immediate",
                        "validate": (options or {}).get("validate", "standard")
                    }
                }
                resp = send_command_with_retry("manage_script", params)
                if isinstance(resp, dict):
                    resp.setdefault("data", {})["normalizedEdits"] = normalized_for_echo
                return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}
            except Exception as e:
                return {"success": False, "message": f"Edit conversion failed: {e}"}

        # If we have anchor_* only (structured), forward to ManageScript.EditScript to avoid raw text path
        if text_ops.issubset({"anchor_insert", "anchor_delete", "anchor_replace"}):
            params: Dict[str, Any] = {
                "action": "edit",
                "name": name,
                "path": path,
                "namespace": namespace,
                "scriptType": script_type,
                "edits": edits,
                "options": {"refresh": "immediate", "validate": (options or {}).get("validate", "standard")}
            }
            resp2 = send_command_with_retry("manage_script", params)
            if isinstance(resp2, dict):
                resp2.setdefault("data", {})["normalizedEdits"] = normalized_for_echo
            return resp2 if isinstance(resp2, dict) else {"success": False, "message": str(resp2)}
        
        # For regex_replace on large files, support preview/confirm
        if "regex_replace" in text_ops and not (options or {}).get("confirm"):
            try:
                preview_text = _apply_edits_locally(contents, edits)
                import difflib
                diff = list(difflib.unified_diff(contents.splitlines(), preview_text.splitlines(), fromfile="before", tofile="after", n=2))
                if len(diff) > 800:
                    diff = diff[:800] + ["... (diff truncated) ..."]
                return {"success": False, "message": "Preview diff; set options.confirm=true to apply.", "data": {"diff": "\n".join(diff)}}
            except Exception as e:
                return {"success": False, "message": f"Preview failed: {e}"}
        # 2) apply edits locally (only if not text-ops)
        try:
            new_contents = _apply_edits_locally(contents, edits)
        except Exception as e:
            return {"success": False, "message": f"Edit application failed: {e}"}

        if preview:
            # Produce a compact unified diff limited to small context
            import difflib
            a = contents.splitlines()
            b = new_contents.splitlines()
            diff = list(difflib.unified_diff(a, b, fromfile="before", tofile="after", n=3))
            # Limit diff size to keep responses small
            if len(diff) > 2000:
                diff = diff[:2000] + ["... (diff truncated) ..."]
            return {"success": True, "message": "Preview only (no write)", "data": {"diff": "\n".join(diff), "normalizedEdits": normalized_for_echo}}

        # 3) update to Unity
        # Default refresh/validate for natural usage on text path as well
        options = dict(options or {})
        options.setdefault("validate", "standard")
        options.setdefault("refresh", "immediate")

        params: Dict[str, Any] = {
            "action": "update",
            "name": name,
            "path": path,
            "namespace": namespace,
            "scriptType": script_type,
            "encodedContents": base64.b64encode(new_contents.encode("utf-8")).decode("ascii"),
            "contentsEncoded": True,
        }
        if options is not None:
            params["options"] = options
        write_resp = send_command_with_retry("manage_script", params)
        if isinstance(write_resp, dict):
            write_resp.setdefault("data", {})["normalizedEdits"] = normalized_for_echo
        return write_resp if isinstance(write_resp, dict) else {"success": False, "message": str(write_resp)}




    # safe_script_edit removed to simplify API; clients should call script_apply_edits directly
