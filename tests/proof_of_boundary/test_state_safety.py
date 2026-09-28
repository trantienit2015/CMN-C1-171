# PB-2 + PB-5: State Safety Verification
# Verifies that State contains only msgpack-safe types (no Pydantic, dataclass, JWT)

import ast
import os
import re
import pytest


CREDENTIAL_FIELD_PATTERNS = re.compile(
    r"(jwt|token|api_key|secret|password|credential|connection_string)", re.IGNORECASE
)

PROHIBITED_TYPE_ANNOTATIONS = [
    "BaseModel",
    "InvocationContext",
]


def _scan_state_file(filepath: str) -> list[str]:
    """Scan a state definition file for safety violations."""
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
        tree = ast.parse(source, filename=filepath)

    violations = []

    for node in ast.walk(tree):
        # Check class definitions that look like State
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id

                    # Check for credential-like field names
                    if CREDENTIAL_FIELD_PATTERNS.search(field_name):
                        violations.append(
                            f"{filepath}:{item.lineno} — Credential-like field name: {field_name}"
                        )

                    # Check for prohibited type annotations
                    if item.annotation:
                        annotation_str = ast.dump(item.annotation)
                        for prohibited in PROHIBITED_TYPE_ANNOTATIONS:
                            if prohibited in annotation_str:
                                violations.append(
                                    f"{filepath}:{item.lineno} — Prohibited type in State: {prohibited}"
                                )

                        # ADR-005: nested containers (dict / list[dict]) are not
                        # msgpack-safe. They must be stored JSON-serialized as
                        # Optional[str] and (de)serialized via to_json/from_json.
                        if _is_bare_container(item.annotation):
                            violations.append(
                                f"{filepath}:{item.lineno} — ADR-005: bare dict/list[dict] "
                                f"State field '{field_name}' (use Optional[str] + to_json/from_json)"
                            )

    return violations


def _is_bare_container(annotation: ast.expr) -> bool:
    """True for a `dict` / `list[dict]` (or list[Any]) State annotation.

    Optional[str] wrappers (`str | None`, `Optional[str]`) are safe and ignored.
    """
    # bare `dict` or `list`
    if isinstance(annotation, ast.Name) and annotation.id in ("dict", "list"):
        return True
    # subscripted: dict[...], list[dict], list[Any]
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        if isinstance(base, ast.Name) and base.id in ("dict", "Dict"):
            return True
        if isinstance(base, ast.Name) and base.id in ("list", "List"):
            inner = annotation.slice
            if isinstance(inner, ast.Name) and inner.id in ("dict", "Dict", "Any"):
                return True
            if isinstance(inner, ast.Subscript) and isinstance(inner.value, ast.Name) \
                    and inner.value.id in ("dict", "Dict"):
                return True
    return False


class TestStateSafety:
    """PB-2/PB-5: State must be msgpack-safe with no credentials."""

    def test_state_file_safety(self):
        """State definition must not contain credential fields or prohibited types."""
        state_file = os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas", "state.py")
        if not os.path.exists(state_file):
            pytest.skip("src/schemas/state.py not found")

        violations = _scan_state_file(state_file)

        assert violations == [], (
            "State safety violations found:\n" + "\n".join(violations)
        )
