# DEVG MC

DEVG MC is a Minecraft 1.20.1 Forge modpack.

## Players

Server address: `forge.devgru-mc.org`

Setup guide: [docs.devgru-mc.org/minecraft](https://docs.devgru-mc.org/minecraft/), starting
with [Setup: Prism Launcher](https://docs.devgru-mc.org/minecraft/setup-prism/).

Two install routes. Prism Launcher installs straight from the packwiz manifest below and
re-syncs with the server on every launch. CurseForge app players install the published
CurseForge project.

## Maintainers

The pack manifest is served at https://stickman112.github.io/devgru-mc-pack/pack.toml, the URL
both the server and the Prism pre-launch hook install from. It is the source of truth for the
modlist; the CurseForge project is a downstream artifact generated from it, never an upstream
source.

Working conventions (the side scheme, the version-pinning policy, the deliberate sidecar
exclusions) are kept in a machine-local `CLAUDE.md`, deliberately untracked because this repo
is public.
