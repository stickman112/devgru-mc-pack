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

Better Weaponry has been removed (devgru-mc-pack#4) and the `unmapped` list is
empty, so every side-relevant jar now has a CF mapping. Pack identity moves with
every mod change and is deliberately NOT restated here; derive it with
`tools/client_drift_check/check.py`, which prints `total entries` and
`expected client-side` off the live pack, or read the canonical Forge block in
dotfiles `minecraft_server_context.md`.

## Usage

```
packwiz curseforge export -o dist/export.zip
python3 tools/cf_export_convert/convert.py dist/export.zip \
    -o dist/DEVG-MC-<version>.zip [--bundle-unmapped]
rm dist/export.zip
```

`dist/` is the staging folder and is gitignored and packwizignored, so build
artifacts never land in the repo root and `packwiz refresh` never indexes them.
Create it if missing (`mkdir -p dist`). The intermediate export zip is large
(tens of MB, it still carries the bundled jars) and is not worth keeping once
the converted artifact exists.

## The converter emits TWO files, and both belong in the staging folder

Alongside the zip it writes a paste-ready release-notes text file, named to match:
`DEVG-MC-1.20.1-r4.zip` yields `DEVG-MC-1.20.1-r4-release-notes.txt`. The text is
pulled from `CHANGELOG.md` at the pack root by matching the `## <version>` heading
and taking the fenced block beneath it, with the heading and fences stripped, so
the file contents are exactly what gets pasted into the CurseForge file
description with no editing.

**The staging folder should always end up holding the zip and its notes together.**
That is the whole point: r3 kept the artifact and its paste text in one folder, an
r4 change briefly split them, and the upload step then depended on remembering to
go and find the text in the repo. Point `-o` at the staging directory and both
files land there.

The version comes from `cf_mapping.json` `manifest.version`, the same value the zip
carries, so the notes cannot describe a different release than the artifact.

`CHANGELOG.md` is located by walking up from the script until `pack.toml` is found,
not by a hardcoded relative path, so moving this directory does not break it.

**If no matching section exists**, the converter prints a loud warning, still writes
the zip, and deliberately writes **no** notes file. An empty or templated notes file
is exactly the thing that gets pasted into CurseForge by mistake, so its absence is
the safer failure. Add the section to `CHANGELOG.md` and re-run, or write the
description by hand.

Both modes produce a manifest whose file list is **198 entries**, read off the actual
export at pack `4051d3f` (2026-07-31). **There is no `fileCount` key in `manifest.json`;
the number is `len(files)`.** Earlier revisions of this README called it "fileCount",
which sends readers looking for a field that does not exist. It was 199 at 1.20.1-r3
(`d363701`), 199 at 1.20.1-r2
(`c6a0d72`) and 159 at 1.20.1-r1, but the r2 and r3 figures do NOT mean the same
thing: r2 was 199 of 200 client mods, one short because Better Weaponry had to be
stripped, while r3 is 199 of 199 with nothing dropped. An unchanged number here is
not evidence the export was a no-op. This number moves with the pack; re-check it
rather than trusting it.

The r3 to 198 drop is the 2026-07-31 pack change: three `both` mods removed, two `both`
added, and DimensionLock added as `side = "server"` so it is correctly absent from the
CLIENT export. The FTB Ranks add later the same day did NOT move it again, also because
it is `side = "server"`. Client-pull was re-derived and confirmed by a real export both
times rather than carried forward.

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

## Share codes are not this artifact

A CurseForge share/profile code is generated from a CF app instance, and it
exports the app's own `installedAddons` list out of `minecraftinstance.json`.
It does NOT read the instance's `mods/` folder. Any jar the app has not
fingerprinted into that list is invisible to the code, even though it sits on
disk and loads fine locally.

That is not hypothetical. On 2026-07-27 a staged instance held 199 jars while
`installedAddons` held 190, with `cachedScans` empty. The generated code
delivered exactly those 190 to an importing machine: the 10 untracked jars were
absent, and one stale entry that was in the list but no longer on disk was
present. Two of the 10 register network channels, so the imported client was
rejected by the server's FML handshake until those jars were copied in by hand.

Consequences worth keeping in mind:

- A share code is only as complete as the CF app's fingerprint state. Counting
  jars in `mods/` does not verify it. Compare against `installedAddons`.
- The `manifest` blob embedded in `minecraftinstance.json` is a third thing
  again and can be stale independently. It held 133 entries in the same
  instance, and it is not what the code ships.
- This converter's output does not share that failure mode. It is generated
  from the packwiz manifest, so its file list is the pack by construction.

## Release verification: the two-instance model

Two CF app instances exist on the maintainer's Mac and they serve different
purposes. Confusing them is how a bad artifact ships.

|  | Authoring instance | Subscriber instance |
|---|---|---|
| Disk directory | `DEVGRU MC` | `DEVG World` |
| App display name | `DEVG World_Local Test` | `DEVG World` |
| Installed from | packwiz sync plus hand-staging | the published CF project file |
| Mutable | yes, by design | no, treat as read-only |
| Used for | team share codes, internal testing | release verification only |
| Exported from | share codes | nothing |

**Display names and directory names diverge.** The authoring instance was renamed in
the app on 2026-08-02 and its directory did NOT follow. Identify an instance by inode
and by the contents of `minecraftinstance.json` (`name`, `manifest.version`,
`projectID`/`fileID`), never by directory name or app label. The gaming PC's instance
directory is ALSO named `DEVGRU MC`, so the same rule applies there.

### The procedure, from r5 onward

Run against the SUBSCRIBER instance after updating the subscription. Never against the
authoring instance: it is mutable by design, so a pass there proves nothing about what
subscribers receive.

**1. Directory identity, BEFORE counting anything.** Any instance claimed to be freshly
installed must have a birth timestamp of today and an inode different from the previous
one.

    stat -f 'inode=%i birth=%SB mtime=%Sm' "<instance>"

This precondition exists because on 2026-08-02 a reinstall was reported as done three
times before it actually landed on disk, and the stale directory would have passed every
count-based check below.

**2. Settledness.** Newest mtime in `mods/`, plus absence of `.part`, `.crdownload`,
`.partial` and zero-byte files. A mid-install count reads low and is indistinguishable
from real drift.

**3. Set equality, NOT count equality.** Diff every `installedAddons` filename against
every `.jar` on disk, in BOTH directions.

    python3 - <<'PY'
    import json, os
    P = "<instance>"
    d = json.load(open(os.path.join(P, "minecraftinstance.json")))
    addons = {a.get("fileNameOnDisk") or (a.get("installedFile") or {}).get("fileName")
              for a in d.get("installedAddons") or []}
    disk = {f for f in os.listdir(os.path.join(P, "mods")) if f.endswith(".jar")}
    print("in addons, not on disk:", sorted(addons - disk))
    print("on disk, not in addons:", sorted(disk - addons))
    PY

Count agreement is NOT sufficient. On 2026-08-02 the known-bad hand-edited authoring
instance read 198 jars against 198 `installedAddons` and would have passed a numeric
test while being the wrong set entirely.

**Expected asymmetry of exactly one entry.** A manifest-installed instance lists the
pack's own zip in `installedAddons` (category Modpacks, `packageType` 5, pathed to
`downloads/`, with `addonID`/`fileID` equal to the instance's own `projectID`/`fileID`).
So `installedAddons` reads N+1 against N jars and that is CORRECT, not drift. Anything
beyond that single zip is real.

**4. Independent folder check** against the live pack.

    python3 tools/client_drift_check/check.py "<instance>/mods"

Expect exit 0 and "instance matches the live pack exactly".

Steps 3 and 4 prove different things and both are needed: step 4 proves the folder
matches the pack, step 3 proves the app's own list matches the folder. The 2026-07-27
failure passed a folder check and still shipped the wrong set.

### Caveat: an owner-machine install does not exercise CDN delivery

The CF app populates a new install by COPYING from its local library when it already
holds the pinned files, rather than downloading them. On the 2026-08-02 r4 verification
all 198 jars arrived with mtimes spanning May through July, preserved from the local
library, with fresh inodes and `nlink=1` (so they were independent copies, not
hardlinks). The resulting SET is still correct, because the app resolves the manifest's
pinned `projectID`/`fileID` references, but the install would have succeeded even if a
referenced file were unavailable to a fresh downloader. **A true cold install on a
library-clean machine is the only test of that path.** Tracked as devgru-mc-pack#12.

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
