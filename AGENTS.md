# AGENTS.md — OpenSpec workflow

## Tech proposal first
When the user provides a project idea or feature request in plain language:
1) Propose 2–3 implementation options (tech stack).
2) For each option, list:
   - dependencies (pyproject.toml)
   - pros/cons
   - risks
3) Ask any missing questions.
Do not write code until one option is selected.

## Prime directive
Work spec-first. The source of truth is OpenSpec documents in this repository.

## Always read first
You can writer code only after user's direct command!
Before coding, read:
- openspec/project.md
- the active change docs in openspec/changes/<change-id>/ (proposal.md, design.md, tasks.md)

## Do not code until
- User give you a command
- Requirements and tasks checklist exist.
- If unclear: ask questions or update proposal/design first.

## Execution protocol
- Implement tasks top-to-bottom.
- Mark tasks in tasks.md:
  - [~] in progress
  - [x] done
- Keep diffs small. Add tests for behavior changes.
- After implementing a task do not forget to update README.md
- You may spawn maximum 6 additional agents:
  - [agents]
      max_threads = 6
      max_depth = 1

## Critical rules:
- The code MUST be well structured, human readable, and comply with PEP8 requirements.
- Use detailed comments in the code.

## Offer testing commands after current task is done

## Output format
- Plan → patch-style changes → commands to run. Answer in Russian
