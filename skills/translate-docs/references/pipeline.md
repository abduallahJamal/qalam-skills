# Pipeline reference

How the files fit together, what the state file means, and how to resume.

## Directory layout

```text
work/
├── source.md              a copy of the input, never edited
└── ar/                    one directory per target language
    ├── chunk0001.md       source chunks, written by `qalam chunk`
    ├── chunk0002.md
    ├── manifest.json      chunk list with hashes and heading paths
    ├── glossary.json      term base (yours to edit)
    ├── run_state.json     which chunks are done, and from what
    ├── output_chunk0001.md
    └── output_chunk0002.md
final.md                   merged output
preview.html               self-contained RTL preview
```

Why a directory per language: translating into Arabic and English at once is
normal, and two runs must never share a state file.

## `manifest.json`

```json
{
  "version": 1,
  "target_chars": 6000,
  "max_chars": 12000,
  "source_sha256": "…",
  "chunks": [
    {
      "id": "chunk0001",
      "file": "chunk0001.md",
      "start_line": 1,
      "end_line": 214,
      "chars": 8214,
      "sha256": "…",
      "heading_path": ["Chapter 1", "Arrival"],
      "has_code": false,
      "has_table": true
    }
  ]
}
```

Chunks are cut on paragraph boundaries, never inside a fenced block, a table, or
a sentence. A chunk larger than `max_chars` is a single unsplittable block
(a huge table or code listing) and is kept whole on purpose.

## `run_state.json`

Per chunk it records four facts:

| Field | Meaning |
| --- | --- |
| `source_sha256` | the source chunk this output was translated from |
| `terms_signature` | a hash of every glossary entry that applied to that chunk |
| `output_sha256` | the output as recorded (detects hand edits) |
| `status` | `translated`, `review`, or `failed` |

`qalam plan` compares those with the current files and returns three lists:

- **translate** — missing output, blank output, changed source, changed terms,
  changed output, or a non-`translated` status.
- **record only** — an output exists but has no state record (a run from before
  the state file existed). Recording is cheap; retranslating is not.
- **unchanged** — nothing to do.

Because `terms_signature` covers aliases, adding an alias to a term re-translates
exactly the chunks where that alias appears. That is the intended behaviour, and
it is why the glossary can be edited mid-run.

## Resuming

Interruptions are normal. To resume:

```bash
python -m qalam plan work/ar --glossary work/ar/glossary.json --target-language ar --json
```

Nothing else. The plan already knows what is left. Do not delete `run_state.json`
unless you intend a full retranslation, and say so if you do.

## Rebuilding after a source edit

If the source file changed, re-chunk it. Chunk boundaries may shift, so the
safe path is:

1. Copy the new source next to the old one (`source.v2.md`).
2. Chunk into a fresh directory (`work/ar-v2`).
3. Copy `glossary.json` across (it is language state, not chunk state).
4. Run the plan. Chunks that are byte-identical to the old ones will still be
   listed as untranslated because the directory is new — so pass
   `--retranslate-untracked` only if you truly want that, or keep the old
   `output_chunk*.md` by matching chunk hashes:

```bash
python - <<'PY'
import json, os, shutil
old, new = "work/ar", "work/ar-v2"
old_manifest = json.load(open(os.path.join(old, "manifest.json")))
new_manifest = json.load(open(os.path.join(new, "manifest.json")))
by_sha = {c["sha256"]: c["id"] for c in old_manifest["chunks"]}
for chunk in new_manifest["chunks"]:
    src_id = by_sha.get(chunk["sha256"])
    if not src_id:
        continue
    src = os.path.join(old, f"output_{src_id}.md")
    dst = os.path.join(new, f"output_{chunk['id']}.md")
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
PY
```

5. `qalam certify work/ar-v2` records the carried-over outputs.
6. Plan again: only genuinely changed chunks are queued.

## Merging

```bash
python -m qalam merge --source-dir work/ar --translated-dir work/ar --out work/final.md --strict
```

`--strict` exits non-zero when a chunk is missing, blank, or unreadable. Without
it, the merge prints warnings; that is only appropriate for an intermediate look.

The merge order is the numeric chunk order, never the file-system order — which
is why chunks are zero-padded to four digits.

## Cost and time

Rough numbers that hold for most models:

| Document | Chunks at 6000 chars | Time at 4 parallel agents |
| --- | --- | --- |
| 20-page paper | 3–5 | minutes |
| 200-page book | 60–90 | 1–2 hours |
| 1000-page manual | 300+ | most of a day |

The gate and the planner exist to make the long runs restartable without
re-paying for finished work.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `merge` reports missing chunks | A chunk was never recorded/written | Plan, translate the listed ids, merge again |
| `plan` says everything is untracked | state file missing or different directory | `qalam certify` to adopt existing outputs |
| `ChunkingError` on write | `--target-chars` below 200 or larger than `--max-chars` | Fix the arguments |
| Output identical to source | The model refused or the file was copied | Re-translate; the gate flags a ratio of 1.0 only outside the expected band |
| Everything re-translates after a glossary edit | A high-frequency term changed | Expected; restore the old target if that was not intended |
