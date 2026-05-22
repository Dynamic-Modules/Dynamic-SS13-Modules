from __future__ import annotations

import re
from dataclasses import dataclass

from dynamic_ss13_modules.errors import ValidationError

REQ_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_.-]+)(?:\s*(?P<op>>=|<=|==|=|>|<)\s*(?P<version>[0-9A-Za-z_.+-]+))?\s*$"
)


@dataclass(frozen=True)
class DependencyRequirement:
    name: str
    op: str | None = None
    version: str | None = None

    def describe(self) -> str:
        if self.op and self.version:
            return f"{self.name} {self.op} {self.version}"
        return self.name


def parse_requirement(value: str) -> DependencyRequirement:
    match = REQ_RE.match(value)
    if not match:
        raise ValidationError(f"invalid dependency requirement: {value!r}")
    op = match.group("op")
    version = match.group("version")
    if bool(op) != bool(version):
        raise ValidationError(f"invalid dependency requirement: {value!r}")
    if op == "=":
        op = "=="
    return DependencyRequirement(name=match.group("name"), op=op, version=version)


def version_tuple(value: str) -> tuple[int, ...]:
    main = value.split("+", 1)[0].split("-", 1)[0]
    parts = main.split(".")
    numbers: list[int] = []
    for part in parts:
        if not part.isdigit():
            raise ValidationError(f"version {value!r} is not a simple semantic version")
        numbers.append(int(part))
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def satisfies(version: str, requirement: DependencyRequirement) -> bool:
    if not requirement.op or not requirement.version:
        return True
    left = version_tuple(version)
    right = version_tuple(requirement.version)
    if requirement.op == "==":
        return left == right
    if requirement.op == ">=":
        return left >= right
    if requirement.op == "<=":
        return left <= right
    if requirement.op == ">":
        return left > right
    if requirement.op == "<":
        return left < right
    raise ValidationError(f"unsupported dependency operator: {requirement.op}")

