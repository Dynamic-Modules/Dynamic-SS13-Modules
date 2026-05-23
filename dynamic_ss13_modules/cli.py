from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dynamic_ss13_modules.build import prepare_build
from dynamic_ss13_modules.errors import DynamicModulesError
from dynamic_ss13_modules.explain import explain_file, load_index, module_summary
from dynamic_ss13_modules.git.updater import (
    apply_update_candidates,
    commit_host_update,
    find_update_candidates,
)
from dynamic_ss13_modules.lockfile import write_lockfile
from dynamic_ss13_modules.manifest import discover_manifests, load_host_config
from dynamic_ss13_modules.module_ops import install_module, remove_module
from dynamic_ss13_modules.registry import load_registries
from dynamic_ss13_modules.resolver import resolve_modules


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DynamicModulesError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dynamic-modules")
    parser.add_argument(
        "--root",
        default=".",
        help="host repository root (default: current directory)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="host config path (default: <root>/dynamic_modules.toml)",
    )
    subparsers = parser.add_subparsers(required=True)

    _command(subparsers, "init", "create a starter host config", cmd_init)
    _command(subparsers, "scan", "discover module manifests", cmd_scan)
    resolve = _command(subparsers, "resolve", "resolve dependencies and load order", cmd_resolve)
    resolve.add_argument("--write-lock", action="store_true", help="write dynamic_modules.lock.json")
    prepare = _command(subparsers, "prepare", "generate disposable build output", cmd_prepare)
    prepare.add_argument("--no-lock", action="store_true", help="do not write dynamic_modules.lock.json")
    _command(subparsers, "doctor", "validate and explain the host/module state", cmd_doctor)
    explain = _command(subparsers, "explain", "explain module interactions for a file", cmd_explain)
    explain.add_argument("file", help="host file to explain")
    preview = _command(subparsers, "preview-file", "print the materialized path for a patched file", cmd_preview_file)
    preview.add_argument("file", help="host file to preview")
    preview.add_argument("--contents", action="store_true", help="print materialized file contents")
    _command(subparsers, "patch-report", "list structured patches from the generated index", cmd_patch_report)
    _command(subparsers, "workspace-generate", "generate a VS Code multi-root workspace", cmd_workspace_generate)
    _command(subparsers, "test-plan", "print module unit-test include plan", cmd_test_plan)
    _command(subparsers, "registry-sync", "load and summarize allowlisted registries", cmd_registry_sync)
    module = subparsers.add_parser("module", help="install or remove module submodules")
    module_subparsers = module.add_subparsers(required=True)
    module_add = _command(module_subparsers, "add", "install a module as a git submodule", cmd_module_add)
    module_add.add_argument("module_id", help="module id to install")
    module_add.add_argument("--repo", help="repository URL/path; when omitted, trusted registries are searched")
    module_add.add_argument("--branch", help="branch to pass to git submodule add")
    module_add.add_argument("--commit", help="commit to check out after adding")
    module_add.add_argument("--path", help="destination path relative to host root")
    module_add.add_argument("--no-prepare", action="store_true", help="do not regenerate lock/build output")
    module_remove = _command(module_subparsers, "remove", "remove an installed module submodule", cmd_module_remove)
    module_remove.add_argument("module_id", help="module id to remove")
    module_remove.add_argument("--path", help="module path relative to host root")
    module_remove.add_argument("--no-prepare", action="store_true", help="do not regenerate lock/build output")
    update = _command(subparsers, "update", "evaluate or apply git update candidates", cmd_update)
    update.add_argument("--apply", action="store_true", help="checkout selected update candidates")
    update.add_argument("--commit", action="store_true", help="commit updated modules and lockfile")
    update.add_argument("--push", action="store_true", help="push the host update commit")
    return parser


def _command(subparsers: argparse._SubParsersAction, name: str, help_text: str, func):
    parser = subparsers.add_parser(name, help=help_text)
    parser.set_defaults(func=func)
    return parser


def _host(args) -> tuple:
    root = Path(args.root).resolve()
    config = Path(args.config).resolve() if args.config else None
    host = load_host_config(root, config)
    manifests = discover_manifests(host)
    graph = resolve_modules(manifests)
    return host, manifests, graph


def cmd_init(args) -> int:
    root = Path(args.root).resolve()
    config_path = Path(args.config).resolve() if args.config else root / "dynamic_modules.toml"
    if config_path.exists():
        print(f"{config_path} already exists")
        return 0
    (root / "dynamic_modules" / "installed").mkdir(parents=True, exist_ok=True)
    (root / "config" / "dynamic_modules").mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                'module_roots = ["dynamic_modules"]',
                'config_dir = "config/dynamic_modules"',
                'lockfile = "dynamic_modules.lock.json"',
                "",
                "[build]",
                'dir = ".dynamic_modules_build"',
                '# target_dme = "tgstation.dme"',
                'materialize_mode = "overlay"',
                "",
                "[update]",
                "minimum_commit_age_hours = 24",
                "direct_push = false",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    print(f"created {config_path}")
    return 0


def cmd_scan(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    manifests = discover_manifests(host)
    if not manifests:
        print("No module manifests found.")
        return 0
    for manifest in manifests:
        print(f"{manifest.id}\t{manifest.version}\t{manifest.manifest_path}")
    return 0


def cmd_resolve(args) -> int:
    host, _manifests, graph = _host(args)
    for line in module_summary(
        {
            "load_order": graph.load_order,
            "modules": {
                module.id: {"version": module.version, "name": module.name}
                for module in graph.modules.values()
            },
        }
    ):
        print(line)
    for warning in graph.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.write_lock:
        write_lockfile(host, graph)
        print(f"wrote {host.lockfile}")
    return 0


def cmd_prepare(args) -> int:
    host, _manifests, graph = _host(args)
    result = prepare_build(host, graph, write_lock=not args.no_lock)
    print(f"generated {result.index_path}")
    print(f"include manifest: {result.include_path}")
    print(f"test manifest: {result.tests_path}")
    print(f"config export: {result.config_path}")
    if result.lockfile_written:
        print(f"wrote {host.lockfile}")
    return 0


def cmd_doctor(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    manifests = discover_manifests(host)
    print(f"host root: {host.root}")
    print(f"host config: {host.path if host.path.exists() else '(defaults)'}")
    print(f"module roots: {', '.join(str(path) for path in host.module_roots)}")
    print(f"manifests discovered: {len(manifests)}")
    graph = resolve_modules(manifests)
    print(f"resolved modules: {len(graph.modules)}")
    print(f"load order: {', '.join(graph.load_order) if graph.load_order else '(none)'}")
    for warning in graph.warnings:
        print(f"warning: {warning}")
    if not host.lockfile.exists():
        print(f"warning: missing lockfile {host.lockfile}")
    if not host.build.build_dir.exists():
        print(f"warning: missing build index; run dynamic-modules prepare")
    else:
        print(f"build dir: {host.build.build_dir}")
    return 0


def cmd_explain(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    index = load_index(host.build.build_dir)
    for line in explain_file(index, args.file):
        print(line)
    return 0


def cmd_preview_file(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    index = load_index(host.build.build_dir)
    key = _relative_key(index, args.file)
    interactions = index.get("files", {}).get(key, [])
    patched = [
        item
        for item in interactions
        if item.get("kind") in {"patch", "module_patch"} and item.get("output_file")
    ]
    if not patched:
        print(f"No materialized patch overlay recorded for {key}.")
        return 0
    output_path = host.build.build_dir / patched[-1]["output_file"]
    print(output_path)
    if args.contents:
        print(output_path.read_text(encoding="utf-8"))
    return 0


def cmd_patch_report(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    index = load_index(host.build.build_dir)
    count = 0
    for file_name, interactions in sorted(index.get("files", {}).items()):
        for item in interactions:
            if item.get("kind") not in {"patch", "module_patch"}:
                continue
            count += 1
            kind = item.get("kind")
            print(
                f"{file_name}:{item.get('anchor_line')} "
                f"{kind} {item.get('module')}:{item.get('id')} "
                f"{item.get('mode')} risk={item.get('risk')}"
            )
    if count == 0:
        print("No structured patches recorded.")
    return 0


def cmd_workspace_generate(args) -> int:
    host, _manifests, graph = _host(args)
    host.build.build_dir.mkdir(parents=True, exist_ok=True)
    workspace_path = host.build.build_dir / "dynamic-modules.code-workspace"
    folders = [{"name": "host", "path": str(host.root)}]
    for module in graph.ordered_modules():
        folders.append({"name": f"module:{module.id}", "path": str(module.root)})
    workspace = {
        "folders": folders,
        "settings": {
            "dynamicSs13Modules.indexPath": ".dynamic_modules_build/index.json"
        },
    }
    workspace_path.write_text(json.dumps(workspace, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"generated {workspace_path}")
    return 0


def cmd_test_plan(args) -> int:
    host, _manifests, graph = _host(args)
    for module in graph.ordered_modules():
        for pattern in module.build.test_files:
            matches = sorted(path for path in module.root.glob(pattern) if path.is_file())
            for path in matches:
                print(f"{module.id}\t{path}")
    return 0


def _relative_key(index: dict, file_value: str) -> str:
    host_root = Path(index["host_root"]).resolve()
    requested = Path(file_value)
    if requested.is_absolute():
        try:
            return requested.resolve().relative_to(host_root).as_posix()
        except ValueError:
            return requested.as_posix()
    return requested.as_posix()


def cmd_registry_sync(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    registries = load_registries(host)
    if not registries:
        print("No registries configured.")
        return 0
    for name, data in registries.items():
        modules = data.get("modules", {})
        count = len(modules) if isinstance(modules, dict) else 0
        print(f"{name}: {count} modules")
    return 0


def cmd_module_add(args) -> int:
    host = load_host_config(
        Path(args.root).resolve(), Path(args.config).resolve() if args.config else None
    )
    install_path = install_module(
        host,
        args.module_id,
        repo=args.repo,
        branch=args.branch,
        commit=args.commit,
        path=args.path,
    )
    print(f"installed {args.module_id} at {install_path}")
    if not args.no_prepare:
        host, _manifests, graph = _host(args)
        prepare_build(host, graph, write_lock=True)
        print(f"wrote {host.lockfile}")
        print(f"generated {host.build.build_dir / 'index.json'}")
    return 0


def cmd_module_remove(args) -> int:
    host, _manifests, graph = _host(args)
    removed_path = remove_module(host, graph, args.module_id, path=args.path)
    print(f"removed {args.module_id} from {removed_path}")
    if not args.no_prepare:
        host, _manifests, graph = _host(args)
        prepare_build(host, graph, write_lock=True)
        print(f"wrote {host.lockfile}")
        print(f"generated {host.build.build_dir / 'index.json'}")
    return 0


def cmd_update(args) -> int:
    host, _manifests, graph = _host(args)
    candidates = find_update_candidates(host, graph)
    changed = [candidate for candidate in candidates if candidate.changed]
    if not candidates:
        print("No git-backed module sources found.")
        return 0
    for candidate in candidates:
        marker = "update" if candidate.changed else "current"
        print(
            f"{candidate.module_id}: {marker} {candidate.current[:12]} -> {candidate.candidate[:12]} "
            f"from origin/{candidate.branch}"
        )
    if not args.apply:
        print("Dry run only. Re-run with --apply to checkout candidates.")
        return 0
    apply_update_candidates(graph, changed)
    host, _manifests, graph = _host(args)
    prepare_build(host, graph, write_lock=True)
    print("applied updates and regenerated build output")
    if args.commit:
        if args.push and not host.update.direct_push:
            raise DynamicModulesError(
                "refusing to push because update.direct_push is false in host config"
            )
        output = commit_host_update(host, host.update.commit_message, push=args.push)
        print(output)
    return 0
