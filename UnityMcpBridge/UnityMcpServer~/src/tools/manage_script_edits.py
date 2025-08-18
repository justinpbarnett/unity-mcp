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
    idx = request.lower().find(keyword)
    if idx >= 0:
        return request[idx + len(keyword):].strip()
    return ""


def _parse_natural_request_to_edits(
    request: str,
    script_name: str,
    file_text: str,
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """Parses a natural language request into a list of edits.

    Returns (edits, message). message is a brief description or disambiguation note.
    """
    req = (request or "").strip()
    if not req:
        return [], "", {}

    edits: List[Dict[str, Any]] = []
    cls = _infer_class_name(script_name)

    # 1) Insert/Add comment above/below/after method (prefer method signature anchor, not attributes)
    m = re.search(r"(?:insert|add)\s+comment\s+[\"'](.+?)[\"']\s+(above|before|below|after)\s+(?:the\s+)?(?:method\s+)?([A-Za-z_][A-Za-z0-9_]*)",
                  req, re.IGNORECASE)
    if m:
        comment = m.group(1)
        pos = m.group(2).lower()
        method = m.group(3)
        position = "before" if pos in ("above", "before") else "after"
        # Anchor on method signature line
        anchor = rf"(?m)^\s*(?:(?:public|private|protected|internal|static|virtual|override|sealed|async|extern|unsafe|new|partial)\s+)*[\w<>\[\],\s]+\b{re.escape(method)}\s*\("
        edits.append({
            "op": "anchor_insert",
            "anchor": anchor,
            "position": position,
            "text": f"    /* {comment} */\n",
        })
        return edits, "insert_comment", {"method": method}

    # 2) Insert method ... after <Method>
    m = re.search(r"insert\s+method\s+```([\s\S]+?)```\s+after\s+([A-Za-z_][A-Za-z0-9_]*)", req, re.IGNORECASE)
    if not m:
        m = re.search(r"insert\s+method\s+(.+?)\s+after\s+([A-Za-z_][A-Za-z0-9_]*)", req, re.IGNORECASE)
    if m:
        snippet = m.group(1).strip()
        after_name = m.group(2)
        edits.append({
            "op": "insert_method",
            "className": cls,
            "position": "after",
            "afterMethodName": after_name,
            "replacement": snippet,
        })
        return edits, "insert_method", {"method": after_name}

    # 3) Replace method <Name> with <code>
    m = re.search(r"replace\s+method\s+([A-Za-z_][A-Za-z0-9_]*)\s+with\s+```([\s\S]+?)```", req, re.IGNORECASE)
    if not m:
        m = re.search(r"replace\s+method\s+([A-Za-z_][A-Za-z0-9_]*)\s+with\s+([\s\S]+)$", req, re.IGNORECASE)
    if m:
        name = m.group(1)
        repl = m.group(2).strip()
        edits.append({
            "op": "replace_method",
            "className": cls,
            "methodName": name,
            "replacement": repl,
        })
        return edits, "replace_method", {"method": name}

    # 4) Delete method <Name> [all overloads]
    m = re.search(r"delete\s+method\s+([A-Za-z_][A-Za-z0-9_]*)", req, re.IGNORECASE)
    if m:
        name = m.group(1)
        edits.append({
            "op": "delete_method",
            "className": cls,
            "methodName": name,
        })
        return edits, "delete_method", {"method": name}

    # 5) Fallback: no parse
    return [], "Could not parse natural-language request", {}


def register_manage_script_edits_tools(mcp: FastMCP):
    @mcp.tool(description=(
        "Apply targeted edits to an existing C# script WITHOUT replacing the whole file. "
        "Preferred for inserts/patches. Accepts plain-English 'request' or structured 'edits'. "
        "Structured ops: replace_class, delete_class, replace_method, delete_method, insert_method, anchor_insert, anchor_delete, anchor_replace. "
        "Text ops (normalized safely): prepend, append, replace_range, regex_replace. For full-file creation, use manage_script(create)."
    ))
    def script_apply_edits(
        ctx: Context,
        name: str,
        path: str,
        edits: List[Dict[str, Any]],
        options: Dict[str, Any] | None = None,
        script_type: str = "MonoBehaviour",
        namespace: str = "",
        request: str | None = None,
    ) -> Dict[str, Any]:
        # If the edits request structured class/method ops, route directly to Unity's 'edit' action.
        # These bypass local text validation/encoding since Unity performs the semantic changes.
        # If user provided a natural-language request instead of structured edits, parse it
        if (not edits) and request:
            # Read to help extraction and return contextual diff/verification
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
            parsed_edits, why, context = _parse_natural_request_to_edits(request, name, contents or "")
            if not parsed_edits:
                return {"success": False, "message": f"Could not understand request: {why}"}
            edits = parsed_edits
            # Provide sensible defaults for natural language requests
            options = dict(options or {})
            options.setdefault("validate", "standard")
            options.setdefault("refresh", "immediate")
            if len(edits) > 1:
                options.setdefault("applyMode", "sequential")

        # Normalize unsupported or aliased ops to known structured/text paths
        normalized_edits: List[Dict[str, Any]] = []
        for e in edits or []:
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
            # Map common aliases
            if op in ("text_replace",):
                e = dict(e)
                e["op"] = "replace_range"
                normalized_edits.append(e)
                continue
            if op in ("regex_delete",):
                # delete first match via regex by replacing with empty
                e = dict(e)
                e["op"] = "regex_replace"
                e.setdefault("text", "")
                normalized_edits.append(e)
                continue
            if op == "regex_replace" and ("replacement" not in e):
                # Normalize alternative text fields into 'replacement' for local preview path
                if "text" in e:
                    e = dict(e)
                    e["replacement"] = e.get("text", "")
                elif "insert" in e or "content" in e:
                    e = dict(e)
                    e["replacement"] = e.get("insert") or e.get("content") or ""
            if op == "anchor_insert" and not (e.get("text") or e.get("insert") or e.get("content") or e.get("replacement")):
                # Upgrade empty insert intent to anchor_delete with guidance
                e = dict(e)
                e["op"] = "anchor_delete"
                normalized_edits.append(e)
                continue
            normalized_edits.append(e)

        edits = normalized_edits

        for e in edits or []:
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
            if op in ("replace_class", "delete_class", "replace_method", "delete_method", "insert_method", "anchor_insert", "anchor_delete", "anchor_replace"):
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
                # Attach a small verification slice when possible
                if isinstance(resp, dict) and resp.get("success"):
                    try:
                        # Re-read around the anchor/method if known
                        method = context.get("method") if 'context' in locals() else None
                        read_params = {
                            "action": "read",
                            "name": name,
                            "path": path,
                            "namespace": namespace,
                            "scriptType": script_type,
                        }
                        read_resp = send_command_with_retry("manage_script", read_params)
                        if isinstance(read_resp, dict) and read_resp.get("success"):
                            data = read_resp.get("data", {})
                            text_all = data.get("contents") or ""
                            if method:
                                import re as _re2
                                pat = _re2.compile(rf"(?m)^.*\b{_re2.escape(method)}\s*\(")
                                lines = text_all.splitlines()
                                around = []
                                for i, line in enumerate(lines, start=1):
                                    if pat.search(line):
                                        s = max(1, i - 5)
                                        e = min(len(lines), i + 5)
                                        around = lines[s-1:e]
                                        break
                                if around:
                                    resp.setdefault("data", {})["verification"] = {"method": method, "lines": around}
                    except Exception:
                        pass
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
            return send_command_with_retry("manage_script", params)
        
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
            return {"success": True, "message": "Preview only (no write)", "data": {"diff": "\n".join(diff)}}

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
        return write_resp if isinstance(write_resp, dict) else {"success": False, "message": str(write_resp)}




    @mcp.tool(description=(
        "Safe script editing wrapper. Accepts natural language 'request' or flexible 'edits' and normalizes to safe structured ops or guarded text edits. "
        "Defaults: validate=standard, refresh=immediate, applyMode=sequential for multi-edits."
    ))
    def safe_script_edit(
        ctx: Context,
        name: str,
        path: str,
        edits: List[Dict[str, Any]] | None = None,
        options: Dict[str, Any] | None = None,
        script_type: str = "MonoBehaviour",
        namespace: str = "",
        request: str | None = None,
    ) -> Dict[str, Any]:
        return script_apply_edits(ctx, name, path, edits or [], options or {}, script_type, namespace, request)
