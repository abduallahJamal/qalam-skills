# Prompts that work

Copy these, fill the placeholders, and send them to a sub-agent or a fresh
session. They are written to be self-contained: a worker that sees only one of
these must be able to do its job without following the whole skill.

## Per-chunk translation

> Translate `<chunk_path>` from `<source_language>` into `<target_language>` and
> write the result to `<output_path>`. Do not create any other file.
>
> Rules:
> 1. Copy every fenced code block, inline code span, URL, file path, and HTML tag
>    byte for byte. Do not translate them, do not reformat them.
> 2. Keep the Markdown structure identical: same number of headings, list items,
>    table rows, links, and images, in the same order.
> 3. Do not add or remove information. No introductions, no summaries, no
>    translator's notes in the body.
> 4. Use the term table below exactly. If a term is missing, choose a rendering
>    and list it under "new terms" in your final message.
> 5. Match the register of the source: `<formal|neutral|technical>`.
> 6. Output only the translated text. No commentary, no code fences around the
>    whole answer.
>
> Term table:
> `<term_table>`
>
> When finished, run:
> `python -m qalam gate --source <chunk_path> --target <output_path> --source-language <src> --target-language <tgt> --glossary <glossary>`
> Fix every error, then reply with the gate summary and any new terms.

## Review pass (different agent, same chunk)

> You are reviewing a translation, not producing one. Compare `<source_path>`
> with `<output_path>` and report defects under these headings: meaning errors,
> omissions, additions, broken code or links, terminology that contradicts
> `<glossary>`, and sentences that read as machine-translated in
> `<target_language>`.
>
> For each defect give: the source sentence, the translated sentence, what is
> wrong, and a suggested fix. Do not rewrite the whole file. If you find no
> defects in a category, write "none" — do not invent findings to look thorough.

## Terminology decision

> Here is a source term and its context: `<quote 2–3 sentences>`.
> Propose one `<target_language>` rendering that a professional translator would
> use in this domain, and up to two alternatives. For each: why it fits, and what
> it collides with. Prefer the term that stays stable when inflected, and that
> does not already mean something else in `<domain>`. Answer in one short table.

## Glossary seeding from an existing translation

> Read `<aligned_source>` and `<aligned_target>`. Extract every proper noun and
> domain term that appears more than twice, with the rendering the translator
> actually used. Output JSON matching the `glossary.json` schema in
> `<skill>/references/pipeline.md`. Mark `confidence: high` only when the same
> rendering appears in every occurrence.

## Whole-document consistency sweep

> Given `<final_target>` and `<glossary>`, list every place where the same source
> concept is rendered two different ways. Ignore legitimate variation in
> pronouns and verb forms. Report as: concept, renderings found, count of each,
> recommended one, and the line numbers to change.

## Adaptive pass for a translated book

Use after the mechanical gate passes, for read-aloud quality:

> Read `<chapter_range>` of `<final_target>` as a reader, not as a checker.
> Flag only: sentences that need a second pass to understand, paragraphs whose
> rhythm is clearly translated, and repeated sentence openings across consecutive
> paragraphs. For each, give the line and a rewritten sentence. Keep the meaning
> identical and keep the length within 10%.

## What not to put in a prompt

- The whole rule set inline. It crowds out the text being translated and
  degrades quality; reference the file instead.
- "Translate naturally" with no further constraint — it invites rewriting.
- "Be accurate" — every model believes it already is. Ask for the specific check.
- A request to skip the gate. If the gate is unavailable, the chunk is recorded
  as `review`, and the report says so.
