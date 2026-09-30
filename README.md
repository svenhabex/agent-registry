# agent-registry

One place for the instructions and skills you use with Claude Code and Codex.

- **Global** instructions and skills are always on, in every project.
- **Catalog** skills are grouped in categories. You copy them into a project only when you need them.

```
instructions/AGENTS.md        global instructions for both tools
instructions/CLAUDE.md        imports AGENTS.md (+ Claude-only instructions)
skills/global/<skill>/        always-on skills
skills/<category>/<skill>/    catalog skills (e.g. coding-styles/angular)
sync.py                       the CLI (Python 3.9+, nothing to install)
```

## Commands

Run commands as `agent-registry <command>`. The first time, before that command exists, run `python3 sync.py init-global` from this repo.
Add `--dry-run` to any command to see what it would do without changing anything.

### `init-global` — set up your machine (run once)

Connects Claude Code and Codex to this registry, so both use the same global instructions and skills.

```sh
python3 sync.py init-global --dry-run   # preview first
python3 sync.py init-global
```

What it does:

1. Links `~/.agent-registry` to this repo.
2. Installs the `agent-registry` command at `~/.local/bin/agent-registry`. If that folder isn't on your PATH yet, it tells you.
3. Copies skills you already had in `~/.claude/skills` or `~/.agents/skills` into `skills/global/`.
4. Replaces the global config paths with links into the registry:

   | Path | Points to |
   | --- | --- |
   | `~/.claude/CLAUDE.md` | `instructions/CLAUDE.md` |
   | `~/.claude/skills` | `skills/global` |
   | `~/.agents/AGENTS.md` | `instructions/AGENTS.md` |
   | `~/.agents/skills` | `skills/global` |
   | `~/.codex/AGENTS.md` | `instructions/AGENTS.md` |

`instructions/AGENTS.md` starts empty. Put your personal instructions there and both tools will use them. `instructions/CLAUDE.md` only contains `@~/.agents/AGENTS.md`, which tells Claude Code to load that file. Anything you add below that line applies to Claude Code only.

Nothing gets deleted: anything already at those paths is renamed to `<name>.bak-<timestamp>`. Running it again is safe.

### `init-project` — prepare a project

Run it inside a project folder to give it a place for project skills that both tools read.

```sh
cd ~/code/my-app
agent-registry init-project
```

It creates:

```
AGENTS.md                         project instructions, empty (both tools use it)
CLAUDE.md                         contains only @AGENTS.md
.agents/skills/                   project skills live here
.claude/skills -> ../.agents/skills
```

Existing files are kept. If `.claude/skills` already had skills in it, they are moved to `.agents/skills/`.

When it's done, it prints the next steps:

1. Install skills with `agent-registry install`.
2. If you use `to-spec`, `to-tickets`, `triage` or `code-review`, open Claude Code or Codex in the project and run `/setup-skill`. `init-project` can't do this step because the skill asks you questions. It records your issue tracker and triage labels in `docs/agents/` and `AGENTS.md`.

### `list` — see what's in the catalog

```sh
agent-registry list
```

```
engineering/
  code-review  (requires: setup-skill)
  implement  (requires: tdd, code-review)
  ...
planning/
  grill-me  (requires: grilling)
  ...
```

### `install` — add catalog skills to a project

Copies skills from the registry into the project's `.agents/skills/`. Run `init-project` first.

```sh
agent-registry install engineering            # every skill in the category
agent-registry install planning/grill-me       # just one skill (plus what it requires)
```

- **Dependencies come along.** Some skills call other skills. `grill-me`, for example, calls `grilling`. `install` copies those too, even from another category. Global skills are skipped because they're always available.
- **Copies, not links.** You can commit the skills with the project.
- **Your edits are safe.** Skills already in the project are skipped. Add `--force` to replace them with the registry version.

A skill declares what it needs in its `SKILL.md` frontmatter:

```yaml
---
name: grill-me
description: ...
metadata:
  requires: grilling
---
```

### `publish` — share a project skill with the registry

You wrote a useful skill inside a project and want to reuse it elsewhere. `publish` copies `.agents/skills/<skill>` into `skills/<category>/` in the registry.

```sh
agent-registry publish my-skill ai-workflows
```

- **Default:** the project keeps its own copy, so it stays committed to git.
- **`--link`:** replaces the project copy with a link to the registry version. Edits in either place then change the same files.
- **`--force`:** overwrites a skill with the same name that's already in the registry.

Use the category `global` to make the skill always on.

## Skills in this registry

Most skills come from [mattpocock/skills](https://github.com/mattpocock/skills), copied so they can be changed here. [UPSTREAM.md](UPSTREAM.md) records the upstream commit, the local changes and the license.

| Category | Skills |
| --- | --- |
| `global` | `teach`, `handoff`, `to-questionnaire`, `setup-skill` |
| `planning` | `grill-me`, `grill-with-docs`, `to-spec`, `to-tickets`, `triage` (+ `grilling`, `domain-modeling`) |
| `engineering` | `implement`, `code-review`, `diagnosing-bugs` (+ `tdd`, `codebase-design`) |

`to-spec`, `to-tickets`, `triage` and `code-review` work with your issue tracker. Before using them in a project, run `/setup-skill` there once. It asks where issues live, which triage labels to use, and how issues are marked as a Spec, Ticket or Bug (for example a GitHub Project "Issue type" field). It then writes the answers to `docs/agents/` and to `AGENTS.md`, and `to-spec`, `to-tickets` and `triage` set the issue type from there. It also asks how to mark an issue as in progress (for example the Project's "Status" field), which `implement` does when it starts on an issue. The order doesn't matter: you can run it before or after installing skills.

## Other settings

Set `AGENT_REGISTRY` to keep the registry somewhere other than `~/.agent-registry`.

## Tests

```sh
python3 -m unittest discover tests -v
```
