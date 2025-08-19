# CLAUDE TASK: Run NL/T editing tests for Unity MCP repo and emit JUnit

You are running in CI at the repository root. Use only the tools that are allowed by the workflow:
- View, GlobTool, GrepTool for reading.
- Bash for local shell (git is allowed).
- BatchTool for grouping.
- MCP tools from server "unity" (exposed as mcp__unity__*).

## Test target
- Primary file: `ClaudeTests/longUnityScript-claudeTest.cs`
- For each operation, prefer structured edit tools (`replace_method`, `insert_method`, `delete_method`, `anchor_insert`, `apply_text_edits`, `regex_replace`) via the MCP server.
- Include `precondition_sha256` for any text path write.

## Output requirements
- Create a JUnit XML at `reports/claude-nl-tests.xml`.
- Each test = one `<testcase>` with `classname="UnityMCP.NL"` or `UnityMCP.T`.
- On failure, include a `<failure>` node with a concise message and the last evidence snippet (10–20 lines).
- Also write a human summary at `reports/claude-nl-tests.md` with checkboxes and the windowed reads.

## Safety & hygiene
- Make edits in-place, then revert them at the end (`git stash -u`/`git reset --hard` or balanced counter-edits) so the workspace is clean for subsequent steps.
- Never push commits from CI.
- If a write fails midway, ensure the file is restored before proceeding.

## NL-0. Sanity Reads (windowed)
- Tail 120 lines of `ClaudeTests/longUnityScript-claudeTest.cs`.
- Show 40 lines around method `Update`.
- **Pass** if both windows render with expected anchors present.

## NL-1. Method replace/insert/delete (natural-language)
- Replace `HasTarget` with block-bodied version returning `currentTarget != null`.
- Insert `PrintSeries()` after `GetCurrentTarget` logging `1,2,3`.
- Verify by reading 20 lines around the anchor.
- Delete `PrintSeries()` and verify removal.
- **Pass** if diffs match and verification windows show expected content.

## NL-2. Anchor comment insertion
- Add a comment `Build marker OK` immediately above the `Update` method.
- **Pass** if the comment appears directly above the `public void Update()` line.

## NL-3. End-of-class insertion
- Insert a 3-line comment `Tail test A/B/C` before the last method or immediately before the final class brace (preview, then apply).
- **Pass** if windowed read shows the three lines at the intended location.

## NL-4. Compile trigger
- After any NL edit, ensure no stale compiler errors:
  - Write a short marker edit, then **revert** after validating.
  - The CI job will run Unity compile separately; record your local check (e.g., file parity and syntax sanity) as INFO, but do not attempt to invoke Unity here.

## T-A. Anchor insert (text path)
- Insert after `GetCurrentTarget`: `private int __TempHelper(int a, int b) => a + b;`
- Verify via read; then delete with a `regex_replace` targeting only that helper block.
- **Pass** if round-trip leaves the file exactly as before.

## T-B. Replace method body with minimal range
- Identify `HasTarget` body lines; single `replace_range` to change only inside braces; then revert.
- **Pass** on exact-range change + revert.

## T-C. Header/region preservation
- For `ApplyBlend`, change only interior lines via `replace_range`; the method signature and surrounding `#region`/`#endregion` markers must remain untouched.
- **Pass** if signature and region markers unchanged.

## T-D. End-of-class insertion (anchor)
- Find final class brace; `position: before` to append a temporary helper; then remove.
- **Pass** if insert/remove verified.

## T-E. Temporary method lifecycle
- Insert helper (T-A), update helper implementation via `apply_text_edits`, then delete with `regex_replace`.
- **Pass** if lifecycle completes and file returns to original checksum.

## T-F. Multi-edit atomic batch
- In one call, perform two `replace_range` tweaks and one comment insert at the class end; verify all-or-nothing behavior.
- **Pass** if either all 3 apply or none.

## T-G. Path normalization
- Run the same edit once with `unity://path/ClaudeTests/longUnityScript-claudeTest.cs` and once with `ClaudeTests/longUnityScript-claudeTest.cs` (if supported).
- **Pass** if both target the same file and no path duplication.

## T-H. Validation levels
- After edits, run `validate` with `level: "standard"`, then `"basic"` for temporarily unbalanced text ops; final state must be valid.
- **Pass** if validation OK and final file compiles in CI step.

## T-I. Failure surfaces (expected)
- Too large payload: `apply_text_edits` with >15 KB aggregate → expect `{status:"too_large"}`.
- Stale file: change externally, then resend with old `precondition_sha256` → expect `{status:"stale_file"}` with hashes.
- Overlap: two overlapping ranges → expect rejection.
- Unbalanced braces: remove a closing `}` → expect validation failure and **no write**.
- Header guard: attempt insert before the first `using` → expect `{status:"header_guard"}`.
- Anchor aliasing: `insert`/`content` alias → expect success (aliased to `text`).
- Auto-upgrade: try a text edit overwriting a method header → prefer structured `replace_method` or return a clear error.
- **Pass** when each negative case returns the expected failure without persisting changes.

## T-J. Idempotency & no-op
- Re-run the same `replace_range` with identical content → expect success with no change.
- Re-run a delete of an already-removed helper via `regex_replace` → clean no-op.
- **Pass** if both behave idempotently.

### Implementation notes
- Always capture pre- and post‑windows (±20–40 lines) as evidence in the JUnit `<failure>` or as `<system-out>`.
- For any file write, include `precondition_sha256` and verify the post‑hash in your log.
- At the end, restore the repository to its original state (`git status` must be clean).

# Emit the JUnit file to reports/claude-nl-tests.xml and a summary markdown to reports/claude-nl-tests.md.
