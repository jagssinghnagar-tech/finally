# Review findings

## [P1] Do not disable the working-directory read boundary globally

`.claude/settings.json:8` sets `blockReadsOutsideWorkingDirectories` to `false`. This weakens the session-wide filesystem isolation, allowing any Claude tool invocation to read files outside the project, including potentially sensitive user files. The Stop hook does not need this broad setting to run `git diff HEAD` or write `planning/REVIEW.md`; remove it, or grant only a narrowly scoped permission if an actual workflow requires it.

## [P1] The Stop hook runs an autonomous writer on every session stop

`.claude/settings.json:11` runs `codex exec` unconditionally when Claude stops, and its prompt directs Codex to overwrite the shared `planning/REVIEW.md`. Stopping a session now depends on Git and Codex being available, and even unrelated or clean sessions modify the review artifact. The hook can also continually review its own configuration change. Make review an explicit command, or gate the hook on relevant staged/source changes and use a uniquely named output rather than a shared file.

## [P1] Resolve the Docker persistence contract in the normative plan

`planning/PLAN.md:399` still specifies a named Docker volume (`finally-data:/app/db`), while the added recommendation at `planning/PLAN.md:482` chooses a bind mount for the project-root `db/` directory. These require different start/stop-script behavior, and the existing instruction not to remove the volume is incorrect for a bind mount. Choose one approach and update the command, directory description, and script requirements together.

## [P1] The promised always-present watchlist price only works for the simulator

The recommendation at `planning/PLAN.md:475` guarantees a synchronous seed price when a ticker is added. That cannot guarantee a price when Massive is selected: an invalid, halted, or not-yet-quoted ticker may produce no quote. Define source-independent validation and a pending/no-quote response (or a synchronous lookup failure contract), so the frontend does not assume a numeric price in real-data mode.

## [P2] Move selected recommendations out of the non-binding review appendix

The new section is expressly non-binding and multiple entries still say "Take best recommendation from your end." Consequently it does not define the manual-trade error shape, zero-quantity handling, chat concurrency rule, or cache-access contract for implementation and tests. Incorporate the final decisions into their relevant normative sections, then remove the provisional Q&A.

## [P3] Remove the trailing blank line

`planning/PLAN.md` adds an extra blank line at EOF. Remove it to keep the documentation clean and satisfy a whitespace check.
