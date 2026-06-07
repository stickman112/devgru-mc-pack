# devgru-mc-pack: Claude Context

Canonical packwiz source of truth for the DEVGRU MC modpack. Minecraft 1.20.1, Forge 47.4.10. Hosted via GitHub Pages; player clients and the Dedic8 Forge server both install from this repo via packwiz-installer.

## What this repo is
- The authoritative modlist. The Dedic8 `devgru-forge-server` and every player client pull mods from here. Humans write the pack (packwiz CLI); installers read it. One-way data flow.
- Pack URL: https://stickman112.github.io/devgru-mc-pack/pack.toml

## Side scheme (client / server / both)
Every mod's `.pw.toml` carries a `side` field:
- `both`   - loads on client and server (the shared pack, 142 mods).
- `client` - client-only (18 mods: minimaps, UI, shader loaders, etc.). Never installed server-side.
- `server` - server-only admin/tooling (4 mods: spark, spark-rest, worldedit, chunky).

Install invocations:
- Server (Dedic8): packwiz-installer with `-s server` pulls both+server = 146 mods.
- Client: packwiz-installer with no side flag (or `-s client`) pulls both+client = 160 mods.

The 146-mod server pull plus the manual sidecars below equals the 147 jars that MODS-FORGE.md (in stickman112/devgru-mc-server) records as loaded. Keep this repo in sync with that manifest; it is the cross-check.

## Version-pinning policy
Pin every mod to the version currently loaded on the server, NOT "latest". When adding or updating, match the server-loaded jar (see MODS-FORGE.md). A count check alone will not catch a version drift, so the pin must be right at add time.

## Add mechanisms by source
- Modrinth: `packwiz modrinth add <slug> --version-filename <exact.jar>`.
- CurseForge: `packwiz cf add --addon-id <id> --file-id <id>` to pin the exact file. Verify `allowModDistribution=true` first (the curse.tools proxy answers without an API key). A non-distributable CF mod cannot be auto-installed and must be handled as a sidecar, not committed here.
- spark-rest (our own fork, stickman112/Spark-REST): `packwiz url add spark-rest <release-asset-url>`. Current: https://github.com/stickman112/Spark-REST/releases/download/v1.1.0/spark_rest-1.1.0.jar . Source jar is built at `~/Projects/Spark-REST/build/libs/spark_rest-1.1.0.jar` on the Mac. It is self-hosted via its own GitHub release because it is our mod; do NOT self-host third-party jars here.

## Deliberate exclusions (NOT in this pack)
Intentionally absent. Do not "fix" the pack by adding them.
- TACZ MW Gun Pack content pack (`mw19_guns_addon_v200.zip`): a TACZ content pack that lives outside `mods/` (in `C:\MinecraftServer\Forge\tacz\` on Dedic8). Manual server-side sidecar. The TACZ framework mod itself (`timeless-and-classics-zero`) IS in the pack as `side="both"`.
- Jake's WorldGuard (`jakesworldguard-1.2.0.jar`): CurseForge project `jakes-world-protection-and-plots`, `allowModDistribution=false`. Non-distributable, so it cannot ship in a public pack. Manual server-side install on Dedic8; already in its `mods/` directory.
- AttributeFix (`AttributeFix-Forge-1.20.1-21.0.5.jar`): removed; parked on Dedic8 in `mods_hold/`. Per MODS-FORGE.md the recorded reason is overlap with Apothic Attributes' attribute-clamping role; that cause was not independently re-verified this session. Check MODS-FORGE.md and `mods_hold/` on Dedic8 for authoritative status before re-adding.
- Sophisticated Backpacks (`sophisticatedbackpacks-1.20.1-3.24.43.1789.jar`): removed; parked on Dedic8 in `mods_hold/`. Per MODS-FORGE.md the recorded reason is a `sophisticatedcore` version requirement the pack did not meet; not re-verified this session. Check MODS-FORGE.md and `mods_hold/` for authoritative status before re-adding.
- Pack-author-disabled jars (Loot Integrations, Chunk Save / smoothchunk): removed; they were `.jar.disabled` on the server. packwiz has no disabled concept, so they are simply absent here.

## Editing the pack
1. Add/remove/retag mods with the packwiz CLI (or hand-edit `side`).
2. `packwiz refresh` to update `index.toml`.
3. Commit and push. (A later phase adds CI to regenerate a human-facing `INSTALLED_MODS.md`.)

## Tooling
- packwiz on the Mac: `~/bin/packwiz` (built from source via `go install`; no brew formula). See dotfiles `mac_environment.md`.
