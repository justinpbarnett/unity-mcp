from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, List
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
            if start_line < 1 or end_line < start_line or end_line > len(lines):
                raise RuntimeError("replace_range out of bounds")
            a = start_line - 1
            b = end_line
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


def register_manage_script_edits_tools(mcp: FastMCP):
    @mcp.tool(description=(
        "Apply targeted edits to an existing C# script WITHOUT replacing the whole file. "
        "Preferred for inserts/patches. Supports ops: anchor_insert, prepend, append, "
        "replace_range, regex_replace. For full-file creation, use manage_script(create)."
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
        # If the edits request structured class/method ops, route directly to Unity's 'edit' action
        for e in edits or []:
            op = (e.get("op") or e.get("operation") or e.get("type") or e.get("mode") or "").strip().lower()
            if op in ("replace_class", "delete_class", "replace_method", "delete_method", "insert_method"):
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

        # 2) apply edits locally
        try:
            new_contents = _apply_edits_locally(contents, edits)
        except Exception as e:
            return {"success": False, "message": f"Edit application failed: {e}"}

        # 3) update to Unity
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



