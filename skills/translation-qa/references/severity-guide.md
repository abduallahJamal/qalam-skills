# Severity guide

The question is not "how bad does this feel" but "what must the reader do about
it".

## Blocking

Publishing this would misinform, break code, or lose content.

- A negation, condition, or requirement is missing or inverted
- A number with a unit is wrong
- Code, a path, a flag, or a URL is changed
- A section, paragraph, or list item is missing
- A link or image is broken
- The output is not in the target language

## Major

A native reader would flag it; the meaning survives.

- Terminology contradicts the glossary
- Idiom calqued into nonsense
- Register drifts within one section
- A sentence requires two readings to parse
- Gender/agreement error that changes who is doing what
- Duplicated clause in one paragraph
- Term left untranslated where a translation exists

## Minor

Noticed by an editor, not by a casual reader.

- Punctuation style (ASCII comma after Arabic)
- Space before punctuation
- Inconsistent transliteration of a minor name
- Sentence-initial repetition across two paragraphs
- Slight over- or under-length of a phrase

## Note

A judgement call that belongs to the author.

- A style preference where both options are correct
- A regional variant (مستودع vs مخزن)
- A deliberate deviation from the glossary that the author approved
- Anything requiring domain expertise to decide

## Borderline cases

| Situation | Call it | Why |
| --- | --- | --- |
| Meaning survives but a clause moved to another sentence | Minor | Structure of the argument is intact |
| A whole sentence split into two | Minor, unless it changes emphasis → Major | Splitting is legitimate editing |
| A metaphor replaced by a plain statement | Major | Voice is lost, not just style |
| Glossary term used once in an otherwise consistent text | Major | Consistency is the glossary's whole job |
| A name transliterated differently from the glossary but recognisable | Major | The glossary is a decision |
| Western digits in an Arabic-Indic document, outside code | Minor | Visible, does not misinform |
| A footnote moved to end of section | Major | Changes reading flow; needs the author's call |

## Reporting volume

A review with 200 minor findings is not read. Report:

- every Blocking and Major finding, individually
- minor findings as a table, capped at 25 rows, plus a count
- a single line for any category with systemic issues ("Arabic commas used
  consistently where the project standard is Western: 47 instances")

Systemic findings are worth more than individual ones: they tell the author where
the process, not the sentence, needs fixing.
