# Apple Music Agent Plugin

Portable Agent Skills package for Apple Music library and playlist workflows. It includes the `apple-music-manager` skill, a local stdio MCP server template, and offline snapshot comparison and playlist verification tools.

## Install and connect

Install [`uv`](https://docs.astral.sh/uv/) and the third-party `applemusic-mcp` package in your environment. Sign in and check the local server before connecting an agent:

```sh
uvx applemusic-mcp login
uvx applemusic-mcp status
```

Register the command from [`mcp.json`](mcp.json) in an Agent Skills/MCP-compatible client. Portable plugin discovery and MCP registration are client-specific; some clients require manual setup. The server runs locally over stdio and does not send credentials through this repository. To work with separate storefronts, create isolated MCP profiles and register a separate named server instance for each profile according to that MCP version and client. Check each instance's status before use.

## Offline helpers

Requires Python 3.10 or newer; no third-party Python packages or network access are needed for these scripts.

```sh
python3 skills/apple-music-manager/scripts/compare_library_snapshots.py \
  --source tests/fixtures/library-source.json \
  --target tests/fixtures/library-target.json \
  --cache tests/fixtures/id-map.json

python3 skills/apple-music-manager/scripts/verify_playlist_snapshots.py \
  --expected tests/fixtures/playlist-expected.json \
  --actual tests/fixtures/playlist-actual.json
```

Both tools produce read-only JSON reports. Consult the skill guide before interpreting candidates or making live changes. Run the offline checks with `python3 -m unittest discover -s tests`.

## Package layout

- `plugin.json`, `mcp.json`: portable package and local MCP declarations.
- `skills/apple-music-manager/`: reusable instructions, scripts, and JSON schemas.
- `tests/fixtures/`: synthetic, account-free examples.

No Apple Music account snapshots, credentials, logs, or session transcripts belong in this repository. See [CONTRIBUTING.md](CONTRIBUTING.md) and [LICENSE](LICENSE).
