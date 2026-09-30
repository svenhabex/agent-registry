# Issue types: GitHub Project field

Issue types are recorded in the **<field name>** single-select field of the GitHub Project **<project title>** (owner `<owner>`, number `<number>`), not as labels.

| Issue type in skills | Option in our project | Option id    |
| -------------------- | --------------------- | ------------ |
| `spec`               | `Spec`                | `<option-id>` |
| `ticket`             | `Ticket`              | `<option-id>` |
| `bug`                | `Bug`                 | `<option-id>` |

- Project node id: `<PVT_...>`
- Field id: `<PVTSSF_...>`

If a command fails with an unknown id, refresh the ids with `gh project field-list <number> --owner <owner> --format json` and update this file.

These commands need the `project` scope on the `gh` token. If it's missing, tell the user to run `gh auth refresh -s project`.

## When a skill says "set the issue type"

1. Add the issue to the project and capture its item id. This is safe to run when the issue is already in the project; it returns the existing item:

   ```sh
   gh project item-add <number> --owner <owner> --url <issue-url> --format json --jq .id
   ```

2. Set the field to the option for the type:

   ```sh
   gh project item-edit --id <item-id> --project-id <PVT_...> --field-id <PVTSSF_...> --single-select-option-id <option-id>
   ```
