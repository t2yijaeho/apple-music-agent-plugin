# Contributing

Keep the package portable across compatible agent clients. Client-specific MCP setup belongs in documentation only when clearly labeled; do not add client adapters without updating the portability scope. Keep examples synthetic and free of account identifiers, private snapshots, tokens, and personal session material.

The helpers use Python 3.10+ and the standard library. Preserve read-only behavior: scripts must not authenticate, contact Apple Music, or mutate accounts. For changes, run:

```sh
python3 -m unittest discover -s tests
python3 -m py_compile skills/apple-music-manager/scripts/*.py
python3 -m json.tool plugin.json > /dev/null
python3 -m json.tool mcp.json > /dev/null
```

Use concise imperative commit subjects (for example, `Clarify isolated profile setup`). Pull requests should describe the affected skill/tool, include validation output, and call out any schema or output-shape changes.
