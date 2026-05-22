from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from dynamic_ss13_modules.errors import ResolveError
from dynamic_ss13_modules.manifest.models import ModuleManifest
from dynamic_ss13_modules.resolver.versioning import parse_requirement, satisfies


@dataclass(frozen=True)
class GraphEdge:
    before: str
    after: str
    reason: str


@dataclass
class ResolvedGraph:
    modules: dict[str, ModuleManifest]
    load_order: list[str]
    edges: list[GraphEdge]
    warnings: list[str] = field(default_factory=list)

    def ordered_modules(self) -> list[ModuleManifest]:
        return [self.modules[module_id] for module_id in self.load_order]


def resolve_modules(manifests: list[ModuleManifest]) -> ResolvedGraph:
    modules: dict[str, ModuleManifest] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for manifest in manifests:
        existing = modules.get(manifest.id)
        if existing:
            errors.append(
                f"duplicate module id {manifest.id!r}: {existing.manifest_path} and {manifest.manifest_path}"
            )
        modules[manifest.id] = manifest
    if errors:
        raise ResolveError("\n".join(errors))

    edges: list[GraphEdge] = []
    for manifest in modules.values():
        _check_requires(manifest, modules, edges, errors)
        _check_optional(manifest, modules, edges)
        _check_conflicts(manifest, modules, errors)
        _apply_load_hints(manifest, modules, edges, warnings)

    if errors:
        raise ResolveError("\n".join(errors))

    load_order = _topological_sort(modules, edges)
    return ResolvedGraph(
        modules=modules,
        load_order=load_order,
        edges=sorted(edges, key=lambda edge: (edge.before, edge.after, edge.reason)),
        warnings=warnings,
    )


def _check_requires(
    manifest: ModuleManifest,
    modules: dict[str, ModuleManifest],
    edges: list[GraphEdge],
    errors: list[str],
) -> None:
    for value in manifest.load.requires:
        requirement = parse_requirement(value)
        dependency = modules.get(requirement.name)
        if not dependency:
            errors.append(f"{manifest.id}: missing required module {requirement.describe()}")
            continue
        if not satisfies(dependency.version, requirement):
            errors.append(
                f"{manifest.id}: requires {requirement.describe()}, but found {dependency.version}"
            )
            continue
        edges.append(GraphEdge(before=dependency.id, after=manifest.id, reason=f"requires {value}"))


def _check_optional(
    manifest: ModuleManifest,
    modules: dict[str, ModuleManifest],
    edges: list[GraphEdge],
) -> None:
    for value in manifest.load.optional:
        requirement = parse_requirement(value)
        dependency = modules.get(requirement.name)
        if dependency and satisfies(dependency.version, requirement):
            edges.append(GraphEdge(before=dependency.id, after=manifest.id, reason=f"optional {value}"))


def _check_conflicts(
    manifest: ModuleManifest, modules: dict[str, ModuleManifest], errors: list[str]
) -> None:
    for value in manifest.load.conflicts:
        requirement = parse_requirement(value)
        other = modules.get(requirement.name)
        if other and satisfies(other.version, requirement):
            errors.append(f"{manifest.id}: conflicts with installed module {other.id} {other.version}")


def _apply_load_hints(
    manifest: ModuleManifest,
    modules: dict[str, ModuleManifest],
    edges: list[GraphEdge],
    warnings: list[str],
) -> None:
    for value in manifest.load.load_after:
        requirement = parse_requirement(value)
        if requirement.name in modules:
            edges.append(GraphEdge(before=requirement.name, after=manifest.id, reason=f"load_after {value}"))
        else:
            warnings.append(f"{manifest.id}: load_after references missing module {requirement.name}")
    for value in manifest.load.load_before:
        requirement = parse_requirement(value)
        if requirement.name in modules:
            edges.append(GraphEdge(before=manifest.id, after=requirement.name, reason=f"load_before {value}"))
        else:
            warnings.append(f"{manifest.id}: load_before references missing module {requirement.name}")


def _topological_sort(modules: dict[str, ModuleManifest], edges: list[GraphEdge]) -> list[str]:
    outgoing: dict[str, set[str]] = defaultdict(set)
    incoming_count: dict[str, int] = {module_id: 0 for module_id in modules}
    for edge in edges:
        if edge.after not in outgoing[edge.before]:
            outgoing[edge.before].add(edge.after)
            incoming_count[edge.after] += 1

    ready = sorted(module_id for module_id, count in incoming_count.items() if count == 0)
    result: list[str] = []
    while ready:
        module_id = ready.pop(0)
        result.append(module_id)
        for after in sorted(outgoing[module_id]):
            incoming_count[after] -= 1
            if incoming_count[after] == 0:
                ready.append(after)
                ready.sort()

    if len(result) != len(modules):
        cycle = sorted(module_id for module_id, count in incoming_count.items() if count > 0)
        raise ResolveError(f"module load-order cycle detected involving: {', '.join(cycle)}")
    return result

