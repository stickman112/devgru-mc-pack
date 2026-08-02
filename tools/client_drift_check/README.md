# client_drift_check

Answers one question: **can a client instance still connect to the server?**

    python3 tools/client_drift_check/check.py "<instance>/mods"

Exit 0 clean or cosmetic, 1 something will block, 2 usage or fetch error.

## When to run it

- **After any pack change that removes a mod with `side = "both"` or `side = "client"`.**
  Before telling anyone the server is ready to join.
- Before generating a CurseForge share code.
- As step 4 of release verification against the SUBSCRIBER instance. See
  `tools/cf_export_convert/README.md`, "Release verification: the two-instance model",
  for the full procedure and for why a folder check alone is not sufficient.
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

## A failed fetch exits 2, it never masquerades as drift

Worth knowing, because the expected set is assembled from roughly 200 sequential HTTP
fetches and the endpoint does fail transiently. A 503 from GitHub Pages and a timeout
to github.com were both observed on 2026-08-02. A partial fetch that silently shrank
the expected set would surface as EXTRA jars in the instance, which is
indistinguishable from real drift.

That cannot happen here. `urlopen` raises `HTTPError` on a non-200 and `TimeoutError`
on a timeout. Both propagate out of `ThreadPoolExecutor.map` when the results are
iterated in `load_live_pack`, and `main` catches them with
`except (urllib.error.URLError, RuntimeError, OSError)`, returning **exit 2**.
`HTTPError` subclasses `URLError`, which subclasses `OSError`, so every network
failure mode lands in that one handler.

So the two counts it prints are either complete or the run never gets far enough to
print them (sample output from the 2026-08-02 r4 verification; both figures move with
the pack, so read them off your own run rather than from this example):

    live pack: https://stickman112.github.io/devgru-mc-pack/pack.toml
      total entries 207 | expected client-side 198

A run that reaches the EXTRA and MISSING report assembled a full expected set. Quote
those two numbers when reporting a result; they are what makes the verdict auditable
after the fact.

## Note on this file

`devgru-mc-pack/CLAUDE.md` is gitignored (public repo), so it cannot carry durable
guidance. This README is tracked and is the source of truth for when to run this check.
See devgru-mc-pack#9 for the broader gitignored-CLAUDE.md problem.

## Requirements

Python 3, stdlib only. Consistent with `cf_export_convert`. `/tools/` is
`.packwizignore`d, so nothing here is ever indexed into the installable pack.
