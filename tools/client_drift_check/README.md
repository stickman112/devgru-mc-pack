# client_drift_check

Answers one question: **can a client instance still connect to the server?**

    python3 tools/client_drift_check/check.py "<instance>/mods"

Exit 0 clean or cosmetic, 1 something will block, 2 usage or fetch error.

## When to run it

- **After any pack change that removes a mod with `side = "both"` or `side = "client"`.**
  Before telling anyone the server is ready to join.
- Before generating a CurseForge share code.
- Any time a player reports being unable to connect after a pack change.

## Why it exists

Prism clients self-heal: packwiz-installer prunes managed files at launch. **The CF app
does not live-sync**, so its instance keeps mods that were removed from the pack. If a
removed mod registers a network channel or content registry entries and does not relax
`displayTest`, the server rejects the client with `Client has mods that are missing on
server`. Those players are locked out, not stale, and the CF republish is blocking.

Happened twice, most recently 2026-07-31 with Valkyrien Skies, Eureka and Better Combat.
See `packwiz_gotchas.md` in dotfiles memory for the full case.

## What it does

1. Reads the **live** pack from GitHub Pages, not the local clone. The clone is routinely
   ahead of what clients actually sync from, so checking against it would pass a client
   that is in fact broken. Fetches are cache-busted, since Pages serves stale content for
   a variable number of seconds after a push.
2. Derives the expected client set as `side = "both"` plus `side = "client"`. An absent
   `side` field means `both`, which is what packwiz writes.
3. Diffs both directions against the instance directory, counting `.jar` anchored so
   `.jar.disabled` files are ignored.
4. For every EXTRA jar, opens it and reports whether it registers a network channel or
   content registry entries and what `displayTest` it declares, then classifies the
   result as `WILL BLOCK` or `cosmetic`.
5. Exits nonzero if anything would block.

## What it deliberately does not do

Missing jars are reported but **not** classified. A missing jar is not a lockout on its
own: it only blocks if that mod registers a channel or registry entries and does not
relax `displayTest`. Classifying it would require reading the jar, which is not present,
and a `metadata:curseforge` pin carries no download URL to fetch it with.

## Note on this file

`devgru-mc-pack/CLAUDE.md` is gitignored (public repo), so it cannot carry durable
guidance. This README is tracked and is the source of truth for when to run this check.
See devgru-mc-pack#9 for the broader gitignored-CLAUDE.md problem.

## Requirements

Python 3, stdlib only. Consistent with `cf_export_convert`. `/tools/` is
`.packwizignore`d, so nothing here is ever indexed into the installable pack.
