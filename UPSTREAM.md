# Upstream skills

Skills copied from [mattpocock/skills](https://github.com/mattpocock/skills) at commit `d81f3a183412e71a5b1e84ca21bc1a35eea03a60` (2026-09-29).

| Registry path | Upstream path |
| --- | --- |
| `skills/global/teach` | `skills/productivity/teach` |
| `skills/global/handoff` | `skills/productivity/handoff` |
| `skills/global/to-questionnaire` | `skills/productivity/to-questionnaire` |
| `skills/global/setup-skill` | `skills/engineering/setup-matt-pocock-skills` |
| `skills/planning/grill-me` | `skills/productivity/grill-me` |
| `skills/planning/grilling` | `skills/productivity/grilling` |
| `skills/planning/grill-with-docs` | `skills/engineering/grill-with-docs` |
| `skills/planning/domain-modeling` | `skills/engineering/domain-modeling` |
| `skills/planning/to-spec` | `skills/engineering/to-spec` |
| `skills/planning/to-tickets` | `skills/engineering/to-tickets` |
| `skills/planning/triage` | `skills/engineering/triage` |
| `skills/engineering/implement` | `skills/engineering/implement` |
| `skills/engineering/tdd` | `skills/engineering/tdd` |
| `skills/engineering/codebase-design` | `skills/engineering/codebase-design` |
| `skills/engineering/code-review` | `skills/engineering/code-review` |
| `skills/engineering/diagnosing-bugs` | `skills/engineering/diagnosing-bugs` |

To see what changed upstream since this copy:

```sh
git clone https://github.com/mattpocock/skills /tmp/mp-skills
git -C /tmp/mp-skills diff d81f3a1 HEAD -- skills/
```

## Local modifications

- Added `metadata: requires:` to the frontmatter of skills that call other skills, so `agent-registry install` copies their dependencies too.
- `setup-skill` (upstream `setup-matt-pocock-skills`): renamed; references in `to-spec`, `to-tickets`, `triage` and `code-review` updated. Step 4 writes the `## Agent skills` block into `AGENTS.md` first (instead of `CLAUDE.md`), so Codex sees it and Claude Code gets it through `@AGENTS.md`. Section B (triage labels) always runs, and `docs/agents/triage-labels.md` is always written, instead of only when `triage` is installed: `to-spec` and `to-tickets` apply these labels too, and `triage` can be installed after setup.
- Issue types: `setup-skill` has a Section D that records how issues are marked as `spec`, `ticket` or `bug` (e.g. a GitHub Project field, template `issue-types-github-project.md`) in `docs/agents/issue-types.md`. `to-spec`, `to-tickets` and `triage` set the type from that file.
- Issue status: `setup-skill` has a Section E that records how an issue is moved to `in-progress` (e.g. a GitHub Project Status field, template `issue-status-github-project.md`) in `docs/agents/issue-status.md`. `implement` moves each issue there when it starts working on it.

## License

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
