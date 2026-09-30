# Testing

What is tested, how, and what the results were. Everything here is reproducible from this repo.

## Automated tests (run in CI on every push)

```bash
python -m unittest discover -s tests -v
```

| Suite | Covers |
|---|---|
| `tests/test_scripts.py` | The dirty-area decoder (edit-only, error-only, edit + error, out-of-range input) and the trace request validator (a good request, a request with planted mistakes, exit codes, warning vs problem) |

The tests are mutation-checked: deliberately breaking the decoder or the validator makes them fail.

## Scenario evaluation (skill vs. no skill)

Three realistic questions with concrete details (see [EXAMPLES.md](EXAMPLES.md); assertions in `plugins/utility-network/skills/utility-network/evals/evals.json`, ids 9 to 11). Each was answered by an isolated agent with no skill and by an isolated agent following the skill, then graded against the assertions by reading the answers. Score is assertions met.

| Scenario | No skill | Skill before fixes | Skill after fixes |
|---|---|---|---|
| 1. Apply Asset Package, gas into water | 5 / 5 | 5 / 5 | not re-run (nothing changed) |
| 2. Isolation trace on `crew1.outage` | 5 / 7 | 5 / 7 | **7 / 7** |
| 3. Dirty areas 1, 2, 9, 8, 40 | 2 / 6 | 5 / 6 | **6 / 6** |

Read the table honestly: one run each, graded by the author, and several assertions were sharpened after the first round exposed the failures, so the "after" column is partly a regression check rather than an independent result. The useful part is the defect list.

## What testing found (and what was fixed)

| Finding | Effect on the answer | Fix |
|---|---|---|
| `rest-api/01` said `sessionId` is required whenever *any* session locks the version. Esri: only when the caller holds the exclusive edit session | The skill-assisted answer told the user to obtain a session for a read-only trace and invented a required placeholder; the no-skill answer got it right | Reference corrected in `rest-api/01` and `rest-api/02`; validator warns when `sessionId` is set; eval assertion fixed |
| Trace response fields were not documented in the skill | Answer filtered results on `assetGroupName`, which does not exist (elements carry codes) | Added the element field list to `rest-api/01` |
| Validate ignores error-only dirty areas (Status 8, 16, 32, 40): only rows with an edit bit are evaluated | The answer said validate re-evaluates and re-writes the error, the opposite of Esri's rule; the fix step "validate again" would do nothing | New section in `pro-help/04`; decoder and evals now state it |
| Subnetworks table fields were partly guessed (`ISDIRTY` unconfirmed) | Advice to filter `ISDIRTY = 1` | Full verified field list in `pro-help/02`; the stored `ISDIRTY` codes are documented as unverified; the `= 1` advice was removed |
| Validator flagged numeric condition values as PROBLEMS although Esri's own example sends `1` | False alarm on a valid request | Now a warning; validator separates PROBLEMS (exit 1) from WARNINGS (exit 0) and gained checks for missing condition `name`, GUID format and category shape |
| Decoder crashed with a traceback on `64` | Poor UX | Clean error, exit status 2 |

## Repeating the scenario evaluation

There is no automated harness for the model-graded part yet. To repeat it: give each prompt in `evals/evals.json` (ids 9 to 11) to a fresh agent with the skill installed and to one without, then check each answer against its `assertions`. Record scores in the table above with the date and skill version. Contributions of a scripted harness are welcome (see ROADMAP).
