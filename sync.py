#!/usr/bin/env python3
"""Manage a central, tool-agnostic skills registry for Claude Code and Codex.

Layout of the registry (default: ~/.agent-registry, a symlink to this repo):

    instructions/CLAUDE.md        global Claude Code instructions
    instructions/AGENTS.md        global Codex instructions
    skills/global/<skill>/        always-on skills (linked into ~/.claude and ~/.agents)
    skills/<category>/<skill>/    catalog skills, installed per project

Commands (run as `agent-registry <command>` after init-global):
    init-global                   create the registry, the global symlinks and the
                                  `agent-registry` command (~/.local/bin/agent-registry)
    init-project                  set up ./AGENTS.md, ./CLAUDE.md, ./.agents/skills and
                                  ./.claude/skills -> ../.agents/skills
    install <category>[/<skill>]  copy registry skills into ./.agents/skills
    publish <skill> <category>    copy ./.agents/skills/<skill> into the registry
    list                          show categories and skills in the registry

Set AGENT_REGISTRY to use a registry location other than ~/.agent-registry.
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT = Path(__file__).resolve()
REPO_DIR = SCRIPT.parent
COMMAND = "agent-registry"
DEFAULT_REGISTRY = "~/.agent-registry"
SAMPLE_CATEGORY = "coding-styles"
# Folder written by claude.ai skill sync into ~/.claude/skills; it is not a skill.
NOT_SKILLS = {"synced"}

# Instructions shared by both tools go in AGENTS.md; CLAUDE.md only imports it,
# so Claude-specific instructions can be added below the import.
GLOBAL_CLAUDE_MD = "@~/.agents/AGENTS.md\n"
PROJECT_CLAUDE_MD = "@AGENTS.md\n"

PROJECT_NEXT_STEPS = """
Next steps:
  1. Add skills:  agent-registry list
                  agent-registry install <category>[/<skill>]
  2. Using to-spec, to-tickets, triage or code-review? Open Claude Code or Codex
     here and run /setup-skill to configure the issue tracker and triage labels.
     Commit docs/agents/ afterwards.
"""

DRY_RUN = False


# --- output helpers ---------------------------------------------------------

def log(action, detail):
    prefix = "[dry-run] " if DRY_RUN else ""
    print(f"{prefix}{action:<10} {detail}")


def die(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def display(path):
    """Show paths relative to the current directory (./...) or home (~/...)."""
    path = Path(path)
    for base, prefix in ((Path.cwd(), "./"), (Path.home(), "~/")):
        try:
            return prefix + str(path.relative_to(base))
        except ValueError:
            pass
    return str(path)


# --- path helpers -----------------------------------------------------------

def registry_root():
    return Path(os.environ.get("AGENT_REGISTRY", DEFAULT_REGISTRY)).expanduser()


def registry_skills():
    return registry_root() / "skills"


def project_skills():
    return Path.cwd() / ".agents" / "skills"


def exists(path):
    """True for files, dirs and symlinks (including broken ones)."""
    return path.exists() or path.is_symlink()


def is_skill_dir(path):
    return path.is_dir() and not path.name.startswith(".") and path.name not in NOT_SKILLS


def skill_dirs(parent):
    if not parent.is_dir():
        return []
    return sorted(p for p in parent.iterdir() if is_skill_dir(p))


def safe_join(base, relative):
    """Join a user-supplied relative path onto base, refusing to escape it."""
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        die(f"invalid path '{relative}': use a relative path like 'coding-styles/angular'")
    return base / rel


# --- filesystem operations (all honour DRY_RUN) ------------------------------

def mkdir(path):
    if path.is_dir():
        return
    if exists(path):
        die(f"{display(path)} exists and is not a directory")
    log("mkdir", display(path))
    if not DRY_RUN:
        path.mkdir(parents=True, exist_ok=True)


def write_if_missing(path, content):
    if exists(path):
        log("exists", display(path))
        return
    log("create", display(path))
    if not DRY_RUN:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def backup(path):
    """Rename path to <name>.bak-<timestamp> next to it and return the new path."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.bak-{stamp}")
    counter = 1
    while exists(target):
        target = path.with_name(f"{path.name}.bak-{stamp}-{counter}")
        counter += 1
    log("backup", f"{display(path)} -> {target.name}")
    if not DRY_RUN:
        path.rename(target)
    return target


def points_to(link, target):
    if not link.is_symlink():
        return False
    current = Path(os.readlink(link))
    if not current.is_absolute():
        current = link.parent / current
    return os.path.normpath(current) == os.path.normpath(target) or (
        current.exists() and current.resolve() == target.resolve()
    )


def ensure_symlink(link, target, relative=False):
    """Make `link` a symlink to `target`, backing up anything already there."""
    if points_to(link, target):
        log("ok", f"{display(link)} -> {display(target)}")
        return
    if link.is_symlink():
        log("unlink", f"{display(link)} (pointed to {os.readlink(link)})")
        if not DRY_RUN:
            link.unlink()
    elif exists(link):
        backup(link)

    source = os.path.relpath(target, link.parent) if relative else str(target)
    log("link", f"{display(link)} -> {source}")
    if DRY_RUN:
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(source, target_is_directory=target.is_dir())
    except OSError as exc:
        hint = ""
        if os.name == "nt":
            hint = " (on Windows, enable Developer Mode or run as administrator to create symlinks)"
        die(f"could not create symlink {link}: {exc}{hint}")


def copy_tree(src, dest, force=False):
    if exists(dest):
        if not force:
            die(f"{display(dest)} already exists (use --force to overwrite)")
        log("replace", display(dest))
        if not DRY_RUN:
            remove(dest)
    log("copy", f"{display(src)} -> {display(dest)}")
    if not DRY_RUN:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, symlinks=True)


# --- commands ---------------------------------------------------------------

def cmd_init_global(args):
    registry = registry_root()
    home = Path.home()

    # Default setup: the registry content lives in this repo and
    # ~/.agent-registry is a symlink to it.
    if "AGENT_REGISTRY" not in os.environ and registry.resolve() != REPO_DIR:
        ensure_symlink(registry, REPO_DIR)
        content_root = REPO_DIR
    else:
        content_root = registry
        mkdir(content_root)

    mkdir(content_root / "instructions")
    write_if_missing(content_root / "instructions" / "CLAUDE.md", GLOBAL_CLAUDE_MD)
    write_if_missing(content_root / "instructions" / "AGENTS.md", "")
    global_skills = content_root / "skills" / "global"
    mkdir(global_skills)
    mkdir(content_root / "skills" / SAMPLE_CATEGORY)

    # Migrate skills from real (non-symlinked) global skill dirs before replacing them.
    for old in (home / ".claude" / "skills", home / ".agents" / "skills"):
        if old.is_symlink() or not old.is_dir():
            continue
        for skill in skill_dirs(old):
            if exists(global_skills / skill.name):
                log("skip", f"{display(skill)} (already in skills/global)")
            else:
                copy_tree(skill, global_skills / skill.name)

    links = [
        (home / ".claude" / "CLAUDE.md", registry / "instructions" / "CLAUDE.md"),
        (home / ".claude" / "skills", registry / "skills" / "global"),
        (home / ".agents" / "AGENTS.md", registry / "instructions" / "AGENTS.md"),
        (home / ".agents" / "skills", registry / "skills" / "global"),
        (home / ".codex" / "AGENTS.md", registry / "instructions" / "AGENTS.md"),
    ]
    for link, target in links:
        ensure_symlink(link, target)
    install_command(home)


def install_command(home):
    """Put an `agent-registry` command on PATH that runs this script."""
    if os.name == "nt":
        log("skip", f"{COMMAND} command (on Windows, run: python {SCRIPT})")
        return
    bin_dir = home / ".local" / "bin"
    ensure_symlink(bin_dir / COMMAND, SCRIPT)
    if not DRY_RUN:
        SCRIPT.chmod(SCRIPT.stat().st_mode | 0o111)
    path_dirs = [os.path.normpath(os.path.expanduser(p)) for p in os.environ.get("PATH", "").split(os.pathsep)]
    if os.path.normpath(bin_dir) not in path_dirs:
        print(f"note: add {display(bin_dir)} to your PATH to use the '{COMMAND}' command")


def cmd_init_project(args):
    root = Path.cwd()
    agents_skills = root / ".agents" / "skills"
    claude_skills = root / ".claude" / "skills"

    mkdir(agents_skills)
    write_if_missing(root / "AGENTS.md", "")
    write_if_missing(root / "CLAUDE.md", PROJECT_CLAUDE_MD)

    # Move skills out of a pre-existing real .claude/skills dir so nothing is lost.
    if claude_skills.is_dir() and not claude_skills.is_symlink():
        for skill in skill_dirs(claude_skills):
            dest = agents_skills / skill.name
            if exists(dest):
                log("skip", f"{skill.relative_to(root)} (already in .agents/skills)")
                continue
            log("move", f"{skill.relative_to(root)} -> {dest.relative_to(root)}")
            if not DRY_RUN:
                shutil.move(str(skill), str(dest))
        if not DRY_RUN and not any(claude_skills.iterdir()):
            claude_skills.rmdir()

    ensure_symlink(claude_skills, agents_skills, relative=True)
    print(PROJECT_NEXT_STEPS)


def read_requires(skill):
    """Skill names listed under `metadata: requires:` in the SKILL.md frontmatter."""
    lines = (skill / "SKILL.md").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"\s+requires:\s*(.*)$", line)
        if match:
            return match.group(1).strip().strip("\"'").split()
    return []


def find_skill(name):
    for category in skill_dirs(registry_skills()):
        if (category / name / "SKILL.md").is_file():
            return category / name
    return None


def with_dependencies(skills):
    """Add the non-global skills that `skills` require, recursively."""
    result = {s.name: s for s in skills}
    queue = list(skills)
    while queue:
        for name in read_requires(queue.pop()):
            if name in result:
                continue
            dep = find_skill(name)
            if dep is None:
                print(f"warning: requires '{name}', which is not in the registry", file=sys.stderr)
            elif dep.parent.name != "global":  # global skills are always available
                result[name] = dep
                queue.append(dep)
    return list(result.values())


def cmd_install(args):
    dest_root = project_skills()
    if not dest_root.is_dir():
        die("./.agents/skills not found; run 'agent-registry init-project' first")

    src = safe_join(registry_skills(), args.path.strip("/"))
    if (src / "SKILL.md").is_file():
        requested = [src]
    elif src.is_dir():
        requested = skill_dirs(src)
        if not requested:
            die(f"category '{args.path}' contains no skills")
    else:
        available = ", ".join(p.name for p in skill_dirs(registry_skills())) or "none"
        die(f"'{args.path}' not found in {display(registry_skills())} (categories: {available})")

    installed = skipped = 0
    for skill in with_dependencies(requested):
        dest = dest_root / skill.name
        if exists(dest) and not args.force:
            log("skip", f"{display(dest)} (already installed)")
            skipped += 1
            continue
        copy_tree(skill, dest, force=args.force)
        installed += 1
    note = f", skipped {skipped} already installed (use --force to overwrite)" if skipped else ""
    print(f"Installed {installed} skill(s) into ./.agents/skills{note}")


def cmd_publish(args):
    name = args.skill_name.strip("/")
    if not name or "/" in name or name in (".", ".."):
        die(f"invalid skill name '{args.skill_name}'")
    src = project_skills() / name
    if src.is_symlink():
        die(f"./.agents/skills/{name} is already a symlink (-> {os.readlink(src)})")
    if not src.is_dir():
        die(f"./.agents/skills/{name} not found")

    category = safe_join(registry_skills(), args.target_category.strip("/"))
    dest = category / name
    copy_tree(src, dest, force=args.force)

    if args.link:
        log("remove", f"./.agents/skills/{name}")
        if not DRY_RUN:
            shutil.rmtree(src)
        ensure_symlink(src, dest)
    print(f"Published {name} to {display(dest)}")


def cmd_list(args):
    root = registry_skills()
    if not root.is_dir():
        die(f"{display(root)} not found; run 'agent-registry init-global' first")
    for category in skill_dirs(root):
        print(f"{category.name}/")
        for skill in skill_dirs(category):
            requires = read_requires(skill) if (skill / "SKILL.md").is_file() else []
            suffix = f"  (requires: {', '.join(requires)})" if requires else ""
            print(f"  {skill.name}{suffix}")


# --- entry point ------------------------------------------------------------

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true",
                        help="print what would happen without changing anything")
    parser = argparse.ArgumentParser(prog=COMMAND, description="Manage the dual-agent skills registry.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-global", parents=[common], help="create the registry and global symlinks") \
        .set_defaults(func=cmd_init_global)
    sub.add_parser("init-project", parents=[common], help="set up AGENTS.md, CLAUDE.md, .agents/ and .claude/ in the current directory") \
        .set_defaults(func=cmd_init_project)

    install = sub.add_parser("install", parents=[common], help="copy a category or skill into ./.agents/skills")
    install.add_argument("path", help="category (coding-styles) or skill (coding-styles/angular)")
    install.add_argument("--force", action="store_true", help="overwrite installed skills")
    install.set_defaults(func=cmd_install)

    publish = sub.add_parser("publish", parents=[common], help="copy a project skill into the registry")
    publish.add_argument("skill_name")
    publish.add_argument("target_category")
    publish.add_argument("--link", action="store_true",
                         help="replace the local copy with a symlink to the registry version")
    publish.add_argument("--force", action="store_true", help="overwrite the registry version")
    publish.set_defaults(func=cmd_publish)

    sub.add_parser("list", parents=[common], help="list registry categories and skills").set_defaults(func=cmd_list)
    return parser


def main(argv=None):
    global DRY_RUN
    args = build_parser().parse_args(argv)
    DRY_RUN = args.dry_run
    args.func(args)


if __name__ == "__main__":
    main()
