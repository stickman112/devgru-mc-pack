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

As of pack identity 206 mods (182 both / 17 client / 7 server; server pull 189,
client pull 199), Better Weaponry has been removed (devgru-mc-pack#4) and the
`unmapped` list is empty, so every side-relevant jar now has a CF mapping.

## Usage

```
packwiz curseforge export -o export.zip
python3 tools/cf_export_convert/convert.py export.zip -o out.zip [--bundle-unmapped]
```

Both modes produce a manifest with fileCount **199**, read off the actual
1.20.1-r3 export (pack `d363701`, 2026-07-27). It was also 199 at 1.20.1-r2
(`c6a0d72`) and 159 at 1.20.1-r1, but the r2 and r3 figures do NOT mean the same
thing: r2 was 199 of 200 client mods, one short because Better Weaponry had to be
stripped, while r3 is 199 of 199 with nothing dropped. An unchanged number here is
not evidence the export was a no-op. This number moves with the pack; re-check it
rather than trusting it.

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

With `unmapped` empty, the two modes are currently equivalent: nothing needs
bundling, so both emit the same zip. Verified against a synthetic export
2026-07-27, both modes exit 0 on an empty `unmapped` list.

**Published upload (strip mode, default).** The 14 CF-mappable mods become
manifest references and `overrides/mods/` ends up empty. This is the shippable
artifact. There is no manual-install footnote for the CF pack description any
more; removing Better Weaponry is what bought that.

**Private Discord bridge zip (`--bundle-unmapped`).** Currently a no-op, kept for
the next time a mod lands with no CF project. It only diverges from strip mode
when `unmapped` is non-empty, in which case those jars stay bundled in
`overrides/mods/` and the zip is for the whitelisted group only, never for
public CF upload.

## Notes

- `allowModDistribution=false` on some mapped mods does not block the CF-app
  path: a CF manifest reference downloads from CurseForge's own CDN via the
  first-party app, which ignores that flag. Only a third-party CF-import launcher
  (Prism/MultiMC) would prompt a manual download for those specific mods, so this
  zip is fit for the CF-app path specifically. **The per-mod tally is UNVERIFIED
  and deliberately not stated.** The previous "6 of the 10" figure was written
  2026-07-15 when `mapped` held 10 entries; `mapped` is now **14** (counted from
  `cf_mapping.json`, 2026-07-27). The flags themselves could NOT be re-checked on
  2026-07-27: both the curse.tools proxy and first-party `api.curseforge.com`
  returned CloudFront edge 403s from this host, so the old numerator was neither
  confirmed nor refuted. Re-count both numbers before quoting either.
- Release-flow placement: the canonical pack push to GitHub Pages is the source
  of truth for Prism clients and the dedicated Forge server. This CF artifact is
  regenerated from the pack whenever it changes and shared out-of-band (CF upload
  and/or Discord); it is not part of the packwiz-installer path. (A later CI
  phase could automate the export + convert step.)
- `stdlib only` (Python 3). `/tools/` is `.packwizignore`d so nothing here is
  ever indexed into the installable pack.
