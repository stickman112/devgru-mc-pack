# devgru-mc-pack: Claude Context

Canonical packwiz source of truth for the DEVGRU MC modpack. Minecraft 1.20.1, Forge 47.4.10. Hosted via GitHub Pages; player clients and the Dedic8 Forge server both install from this repo via packwiz-installer.

## What this repo is
- The authoritative modlist. The Dedic8 `devgru-forge-server` and every player client pull mods from here. Humans write the pack (packwiz CLI); installers read it. One-way data flow.
- Pack URL: https://stickman112.github.io/devgru-mc-pack/pack.toml (live, public)

## Side scheme (client / server / both)
Every mod's `.pw.toml` carries a `side` field. Current totals (162 mods):
- `both`   - loads on client and server (141 mods).
- `client` - client-only (17 mods: minimaps, UI, shader loaders, etc.). Never installed server-side.
- `server` - server-only admin/tooling (4 mods: spark, spark-rest, worldedit, chunky).

Install invocations:
- Server (Dedic8): packwiz-installer with `-s server` pulls both+server = 145 mods.
- Client: packwiz-installer with no side flag (or `-s client`) pulls both+client = 158 mods.

## Loaded-total reconciliation (the cross-check)
Dedic8 loads 147 jars (per MODS-FORGE.md in stickman112/devgru-mc-server):

    packwiz `-s server` pull (145) + 2 jar sidecars = 147 loaded jars

Keep this identity true; if it drifts, either the pack or MODS-FORGE.md is wrong.

## Sidecars (on Dedic8 but deliberately NOT in this pack)
Three sidecars. The first two are the +2 above; the third is not a `mods/` jar.
1. **jakesworldguard** (`jakesworldguard-1.2.0.jar`) - jar, server. CF project `jakes-world-protection-and-plots`, `allowModDistribution=false` (non-distributable, cannot ship in a public pack). In Dedic8 `mods/`.
2. **adaptive_performance_tweaks_player** (`..._player_1.20.1-11.6.1.jar`) - jar, server. 11.6.1 Forge/1.20.1 is non-distributable on CF and absent from Modrinth (caps at 11.6.0); also `client_side=unsupported`, so clients never need it. In Dedic8 `mods/`.
3. **TACZ MW Gun Pack** (`mw19_guns_addon_v200.zip`) - NOT a `mods/` jar. A TACZ content pack in `C:\MinecraftServer\Forge\tacz\`, outside `mods/`; not in the 147 count. The TACZ framework mod (`timeless-and-classics-zero`) IS in the pack as `side="both"`.

## Dropped / not present (do not re-add to "fix" the pack)
- **enhanced-boss-bars**: dropped. No Forge build on Modrinth, non-distributable on CF, cosmetic client mod, known dedicated-server crasher. Clients lose a cosmetic boss-bar styling vs the old CF pack (onboarding footnote).
- **AttributeFix**, **Sophisticated Backpacks**: held on Dedic8 in `mods_hold/`. Reasons recorded in MODS-FORGE.md; not re-verified here. Check there before re-adding.
- **Loot Integrations**, **Chunk Save / smoothchunk**: were `.jar.disabled` on the server; packwiz has no disabled concept, so simply absent.

## Version-pinning policy
Pin every mod to the version currently loaded on the server, NOT "latest" (see MODS-FORGE.md). A count check alone will not catch version drift, so the pin must be right at add time.

## Add mechanisms by source
- **Modrinth**: `packwiz modrinth add <slug> --version-filename <exact.jar>`. CAUTION: `--version-filename` silently falls back to LATEST if it does not match (naming changes across versions); for a hard pin use `--project-id <id> --version-id <id>` together (not with a slug; neither alone). After every add, RE-CHECK `side`: packwiz auto-assigns it from the project's Modrinth client/server metadata and overrides your intended value.
- **CurseForge**: `packwiz cf add --addon-id <id> --file-id <id>` to pin the exact file. Verify `allowModDistribution=true` FIRST (curse.tools proxy, no API key). A non-distributable CF mod aborts packwiz-installer for everyone; re-source from Modrinth or sidecar it. (This pack re-sourced 7 such mods to Modrinth, sidecar'd 1.)
- **spark-rest** (our own fork): `packwiz url add spark-rest <release-asset-url>`. Current: https://github.com/stickman112/Spark-REST/releases/download/v1.1.0/spark_rest-1.1.0.jar . Source jar at `~/Projects/Spark-REST/build/libs/`. Self-hosted via its own GitHub release because it is our mod; do NOT self-host third-party jars here.

## .packwizignore (required)
`packwiz refresh` indexes EVERY file in the repo, including repo-meta files. Without `.packwizignore`, CLAUDE.md / README.md / a gitignored checkpoint get indexed and installed into players' and the server's pack dir (and a gitignored file 404s and aborts the installer). Patterns must be ROOT-ANCHORED with a leading `/`, or they over-match nested pack files (an unanchored `README.md` matched a mod's own `config/.../README.md`).

## Editing the pack
1. Add/remove/retag with the packwiz CLI (or hand-edit `side`); re-check `side` after Modrinth adds.
2. `packwiz refresh` to update `index.toml`.
3. Verify the index delta is only what you intended (no stray files indexed, no nested files dropped by an ignore over-match).
4. Commit and push. (A later phase adds CI to regenerate a human-facing `INSTALLED_MODS.md`, already excluded by `.packwizignore`.)

## Redistribution note
`resourcepacks/Quark Programmer Art.zip` is Quark's resourcepack; Quark is CC-BY-NC-SA-3.0. Redistribution here is permitted (non-commercial, attribution to Quark/Vazkii, share-alike).

## Tooling
- packwiz on the Mac: `~/bin/packwiz` (built from source via `go install`; no brew formula). See dotfiles `mac_environment.md` and `packwiz_gotchas.md`.
