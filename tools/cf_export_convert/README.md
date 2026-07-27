# cf_export_convert

Turns a `packwiz curseforge export` zip into a shareable CurseForge modpack zip
with ZERO bundled mod jars for the mapped mods. Part of the issue #3 CF
distribution artifact.

## Why

The CF app has no pre-launch command field, so packwiz cannot live-sync through
it the way it does in Prism. To give CF-app players a pack, we publish a
downstream CurseForge modpack zip. packwiz stays the single source of truth; the
CF zip is a generated artifact, never hand-edited.

`packwiz curseforge export` alone is not shippable: it bundles every
non-CurseForge (Modrinth/url) mod as a jar in `overrides/mods/`, which

1. redistributes jars whose licenses forbid it (e.g. Pufferfish's Skills forbids
   reupload), and
2. CF moderation rejects unless each bundled jar is on the Approved
   Non-CurseForge Mods list.

This converter replaces each bundlable mod with a CurseForge manifest reference
at its exact pinned version, so the shipped zip carries no third-party jars.

## Usage

```
packwiz curseforge export -o export.zip
python3 tools/cf_export_convert/convert.py export.zip -o out.zip [--bundle-unmapped]
```

Both modes produce a manifest with fileCount 199 (as of pack `c6a0d72`,
2026-07-26; was 159 at the 1.20.1-r1 release). This number moves with the pack;
re-check it rather than trusting it.

- `convert.py` removes the mapped jars from `overrides/mods/`, appends their
  `{projectID, fileID, required:true}` to `manifest.json`, and sets manifest
  `name`/`version`/`author` from the mapping file.
- `cf_mapping.json` (next to the script) is the CF id map: each Modrinth-sourced
  side-relevant jar filename maps to its CF `projectID`/`fileID`, matched by
  exact filename. **Bump `manifest.version` per published release, and
  re-verify ids when a mapped mod's pinned version changes.**
- Safety guard: the converter refuses to run if `overrides/mods/` contains any
  jar not listed in the mapping, so it never ships an unmapped jar blind.
- **Keep the mapping in step with the pack, and do it at add time.** Any mod that
  is Modrinth-sourced or otherwise not a CF reference gets bundled into
  `overrides/mods/` on export, so it needs a mapping entry. The failure mode of
  forgetting is SILENT until someone next tries to publish: the guard refuses,
  which is correct, but discovery lags the pack change arbitrarily. Observed
  2026-07-26, when four unmapped jars (`alcocraftplus`, `fdbosses`, and both
  Let's Do jars) had accumulated since `d08ae86` and the artifact had been
  un-generatable for five days with no signal. After any mod add, run the export
  plus converter as a dry check, or at minimum grep the new filenames against
  `cf_mapping.json`.

## Two modes

**Published upload (strip mode, default).** The 14 CF-mappable mods become
manifest references; Better Weaponry is dropped (it has no CF project, is not on
the Approved Non-CurseForge Mods list, and cannot ship bundled). `overrides/mods/`
ends up empty. A published-pack client must install Better Weaponry manually
(Modrinth download into the profile `mods/` folder) or it fails the Forge
handshake against the server. Document this in the CF pack description.

**Private Discord bridge zip (`--bundle-unmapped`).** Identical, except Better
Weaponry stays bundled in `overrides/mods/` so the zip is complete (160 mods).
For direct sharing with the whitelisted group only, never for public CF upload.

## Notes

- `allowModDistribution=false` on 6 of the 10 mapped mods does not block the
  CF-app path: a CF manifest reference downloads from CurseForge's own CDN via
  the first-party app, which ignores that flag. Only a third-party CF-import
  launcher (Prism/MultiMC) would prompt manual download for those 6, so this zip
  is fit for the CF-app path specifically.
- Release-flow placement: the canonical pack push to GitHub Pages is the source
  of truth for Prism clients and the dedicated Forge server. This CF artifact is
  regenerated from the pack whenever it changes and shared out-of-band (CF upload
  and/or Discord); it is not part of the packwiz-installer path. (A later CI
  phase could automate the export + convert step.)
- `stdlib only` (Python 3). `/tools/` is `.packwizignore`d so nothing here is
  ever indexed into the installable pack.
