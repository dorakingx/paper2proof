"""Code and URL boundaries enforced outside model prompts."""

from __future__ import annotations

import ast
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


class SecurityViolation(ValueError):
    """Raised when untrusted input crosses a hard security boundary."""


PROMPT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "developer message",
    "exfiltrate",
    "aws_access_key_id",
    "instance metadata",
    "169.254.169.254",
)

FORBIDDEN_IMPORT_ROOTS = {
    "asyncio",
    "builtins",
    "ctypes",
    "http",
    "importlib",
    "multiprocessing",
    "os",
    "pathlib",
    "requests",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "urllib",
}
ALLOWED_IMPORT_ROOTS = {"hashlib", "json", "math", "statistics"}
FORBIDDEN_CALLS = {"breakpoint", "compile", "eval", "exec", "input", "open", "__import__"}


@dataclass(frozen=True)
class CodeSafetyResult:
    node_count: int
    imports: tuple[str, ...]


def detect_prompt_injection(text: str) -> list[str]:
    lowered = text.casefold()
    return [marker for marker in PROMPT_INJECTION_MARKERS if marker in lowered]


def validate_python_code(code: str, *, max_nodes: int = 500) -> CodeSafetyResult:
    if len(code.encode()) > 20_000:
        raise SecurityViolation("code exceeds the 20 KB execution limit")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise SecurityViolation(f"invalid Python syntax: {exc.msg}") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > max_nodes:
        raise SecurityViolation("code exceeds the syntax-node limit")

    imports: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise SecurityViolation("relative imports are not allowed")
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                raise SecurityViolation(f"call to {node.func.id!r} is not allowed")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SecurityViolation("dunder attribute access is not allowed")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            raise SecurityViolation("global and nonlocal declarations are not allowed")

    forbidden = imports & FORBIDDEN_IMPORT_ROOTS
    unknown = imports - ALLOWED_IMPORT_ROOTS
    if forbidden:
        raise SecurityViolation(f"forbidden imports: {', '.join(sorted(forbidden))}")
    if unknown:
        raise SecurityViolation(f"imports not on the allowlist: {', '.join(sorted(unknown))}")
    return CodeSafetyResult(node_count=len(nodes), imports=tuple(sorted(imports)))


def _reject_non_public_ip(address: str) -> None:
    ip = ipaddress.ip_address(address)
    if not ip.is_global:
        raise SecurityViolation(f"host resolves to a non-public address: {ip.compressed}")


def normalize_public_url(
    value: str,
    *,
    allowed_hosts: frozenset[str],
    resolve_dns: bool = True,
) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https":
        raise SecurityViolation("only https URLs are accepted")
    if parts.username or parts.password:
        raise SecurityViolation("URL credentials are not accepted")
    if not parts.hostname:
        raise SecurityViolation("URL host is required")

    try:
        host = parts.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise SecurityViolation("invalid internationalized hostname") from exc

    if host == "localhost" or host.endswith(".localhost"):
        raise SecurityViolation("localhost is not accepted")
    if host not in allowed_hosts:
        raise SecurityViolation(f"host is not on the source allowlist: {host}")

    try:
        ipaddress.ip_address(host)
    except ValueError:
        if resolve_dns:
            try:
                addresses = {
                    item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
                }
            except socket.gaierror as exc:
                raise SecurityViolation("source hostname could not be resolved") from exc
            if not addresses:
                raise SecurityViolation("source hostname resolved to no addresses") from None
            for address in addresses:
                _reject_non_public_ip(str(address))
    else:
        _reject_non_public_ip(host)

    port = parts.port
    if port not in (None, 443):
        raise SecurityViolation("only the default HTTPS port is accepted")
    clean_path = parts.path or "/"
    return urlunsplit(("https", host, clean_path, parts.query, ""))
