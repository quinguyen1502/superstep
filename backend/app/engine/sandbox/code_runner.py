"""Runs one Tool node Code call. Executed INSIDE the sandbox as ``python -I -c <this file>``.
Never imported by the server: it uses the standard library only, so any Python 3 image can run it.

stdin: one JSON object {"source", "state", "stdout_max"}.
stdout: the last line is one JSON object, either {"ok": true, "value", "stdout"} or
{"ok": false, "kind": "invalid" | "failed" | "not_json", "error", "traceback", "stdout", "type"}."""
import contextlib, io, json, linecache, os, sys, traceback

FILE = "<code>"


def _result(obj):
    sys.__stdout__.write("\n" + json.dumps(obj, ensure_ascii=False) + "\n"); sys.__stdout__.flush()


def _clip(text, limit):
    data = text.encode("utf-8", "replace")
    if len(data) <= limit: return text
    return data[:limit].decode("utf-8", "ignore") + f"\n…[{len(data) - limit} more bytes]"


def _traceback(exc):
    """Only the user's own frames, with their source lines."""
    te = traceback.TracebackException.from_exception(exc)
    te.stack = traceback.StackSummary.from_list([f for f in te.stack if f.filename == FILE])
    return "".join(te.format()).strip()


BLOCKED = ("socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.system", "pty.", "ctypes.")


def _refuse(event, _args):
    if event.startswith(BLOCKED):
        raise PermissionError(f"{event} is not allowed here: Code nodes have no network and cannot start processes")


def main():
    req = json.loads(sys.stdin.read())
    # STUDIO_CODE_NO_NETWORK=1 (the sandbox service): an audit hook, which cannot be removed once added, refuses sockets,
    # new processes and ctypes for the user's code. It is a guard inside the interpreter, not a kernel boundary.
    if os.environ.get("STUDIO_CODE_NO_NETWORK") == "1": sys.addaudithook(_refuse)
    source, limit = req["source"], int(req.get("stdout_max") or 65536)
    linecache.cache[FILE] = (len(source), None, source.splitlines(True), FILE)
    out = io.StringIO()
    try:
        code = compile(source, FILE, "exec")
    except SyntaxError as exc:
        return _result({"ok": False, "kind": "invalid", "error": f"SyntaxError: {exc.msg} (line {exc.lineno})",
                        "traceback": "".join(traceback.format_exception_only(type(exc), exc)).strip(), "stdout": ""})
    ns = {"__name__": "__studio_code__"}
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            exec(code, ns)
            fn = ns.get("main")
            if not callable(fn):
                return _result({"ok": False, "kind": "invalid", "error": "define a function main(state)", "traceback": "",
                                "stdout": _clip(out.getvalue(), limit)})
            value = fn(req["state"])
    except BaseException as exc:  # SystemExit and KeyboardInterrupt are the code's failures too
        last = traceback.format_exception_only(type(exc), exc)[-1].strip()
        return _result({"ok": False, "kind": "failed", "error": last, "traceback": _traceback(exc), "stdout": _clip(out.getvalue(), limit)})
    stdout = _clip(out.getvalue(), limit)
    try:
        _result({"ok": True, "value": value, "stdout": stdout})
    except (TypeError, ValueError):
        _result({"ok": False, "kind": "not_json", "type": type(value).__name__, "error": "", "traceback": "", "stdout": stdout})


main()
