# Caching strategy for the parse pipeline

Every request re-parses the document, which costs 40 ms on a 2 MB file. Caching the
parsed tree removes that cost for repeat reads, but a stale cache is worse than no
cache: readers act on structure that no longer exists.

## What to cache

Cache the **parsed tree**, not the raw bytes. Use the file's SHA-256 as the key, and
store the parser version alongside it. A parser upgrade must invalidate the whole
cache, because the same bytes can produce a different tree.

See [the parser notes](https://example.com/parser) for the tree shape.

## Invalidation rules

1. Key on file content, never on the path.
2. Include the parser version in the key.
3. Drop entries after 500 MB or 7 days, whichever comes first.

```python
def cache_key(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{PARSER_VERSION}:{digest}"
```

A cache hit must produce a tree that is byte-identical to a fresh parse. If it does
not, the bug is in the cache, not in the parser.
