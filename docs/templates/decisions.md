# Decision index

Copied to `memory-bank/decisions/decisions.md` at bootstrap and translated into the working
language recorded in `techContext.md`. Technical tokens stay in English verbatim.

This file is read at the start of every task, so it stays a table: one line per active decision.
The detail lives in `NNNN-short-title.md` and is read only when needed. What earns a record, the
numbering and status rules, and the structure of a record are defined in `docs/decision-format.md`;
the immutability and supersede rules are in `CLAUDE.md`, *Decisions*.

| No. | Decision | Status |
|---|---|---|

Example rows, for shape only — they are not decisions and are not copied into the table above:

```text
| 0001 | Repository layout: one tree per runtime, tests mirror the source | active           |
| 0002 | Exchange between runtimes: versioned JSON file contract          | superseded by 0007 |
| 0003 | Pre-authorised zone: tests, formatting, docstrings — unasked     | active           |
```

`tools/check-docs.py` checks this table against the files in this directory: every number listed
must have a record, and every record must be listed.
