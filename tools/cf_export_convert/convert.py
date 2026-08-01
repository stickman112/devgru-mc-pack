#!/usr/bin/env python3
"""cf_export_convert: turn a `packwiz curseforge export` zip into a shareable
CurseForge modpack zip with ZERO bundled mod jars for the mapped mods.

For every Modrinth-sourced side=both jar that packwiz bundled into
overrides/mods/, this replaces the jar with a CurseForge manifest reference
({projectID, fileID, required:true}) at the exact pinned version, using the
mapping in cf_mapping.json (next to this script).

Better Weaponry has no CurseForge project, so it cannot become a reference:
  - default (strip mode): drop the jar entirely. Required for a published CF
    upload (CF moderation requires bundled non-CF mods to be on the Approved
    Non-CurseForge Mods list; BW is not). A published-pack client must install
    BW manually from Modrinth or it fails the Forge handshake.
  - --bundle-unmapped: keep the BW jar bundled in overrides (private Discord
    bridge zip only, not for public upload).

Alongside the zip it also writes a paste-ready release-notes text file, pulled
from CHANGELOG.md at the pack root by matching the version heading, so the
staging folder always holds the artifact and the text that goes in the
CurseForge file description together. OUT.zip yields OUT-release-notes.txt.

stdlib only. Usage:
  convert.py EXPORT.zip -o OUT.zip [--bundle-unmapped] [--mapping cf_mapping.json]
"""

import argparse
import json
import os
import sys
import zipfile

MANIFEST = "manifest.json"
MODS_PREFIX = "overrides/mods/"


def die(msg):
    sys.stderr.write("error: " + msg + "\n")
    sys.exit(1)


def load_mapping(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("manifest", "mapped", "unmapped"):
        if key not in data:
            die("mapping file missing '%s'" % key)
    return data


def override_mod_jars(zf):
    """Return {basename: full_zip_path} for every jar under overrides/mods/."""
    out = {}
    for name in zf.namelist():
        if name.startswith(MODS_PREFIX) and name.lower().endswith(".jar"):
            out[os.path.basename(name)] = name
    return out


def find_pack_root(start):
    """Walk up from `start` looking for pack.toml, which marks the pack root.

    Deliberately not a hardcoded relative path: the script keeps working if the
    tools directory is ever moved or the repo is checked out somewhere else.
    """
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, "pack.toml")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def extract_release_notes(changelog_path, version):
    """Return the paste-ready block for `version` from CHANGELOG.md, or None.

    Matches a '## <version>' heading, then returns the contents of the first
    fenced block beneath it. The heading and the fences are stripped, so what
    lands on disk is exactly what gets pasted into the CurseForge file
    description with no editing.
    """
    try:
        with open(changelog_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None

    target = "## " + version
    i = 0
    while i < len(lines) and lines[i].strip() != target:
        i += 1
    if i >= len(lines):
        return None

    # Find the opening fence, but stop if the next release heading arrives first.
    while True:
        i += 1
        if i >= len(lines):
            return None
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            return None
        if stripped.startswith("```"):
            break

    body = []
    i += 1
    while i < len(lines) and not lines[i].strip().startswith("```"):
        body.append(lines[i])
        i += 1
    if i >= len(lines):
        return None  # unterminated fence
    return "\n".join(body).strip("\n") + "\n"


def notes_path_for(output_zip):
    base = output_zip[:-4] if output_zip.lower().endswith(".zip") else output_zip
    return base + "-release-notes.txt"


def main():
    ap = argparse.ArgumentParser(description="Convert a packwiz CF export to a zero-bundle CF modpack zip.")
    ap.add_argument("export_zip", help="Input packwiz curseforge export .zip")
    ap.add_argument("-o", "--output", required=True, help="Output .zip path")
    ap.add_argument("--bundle-unmapped", action="store_true",
                    help="Keep unmapped jars (e.g. Better Weaponry) bundled in overrides. Private Discord zip only; NOT for public CF upload.")
    ap.add_argument("--mapping", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cf_mapping.json"),
                    help="Path to cf_mapping.json (default: next to this script)")
    args = ap.parse_args()

    if not os.path.isfile(args.export_zip):
        die("export zip not found: %s" % args.export_zip)
    mapping = load_mapping(args.mapping)
    mapped = mapping["mapped"]
    unmapped = mapping["unmapped"]
    mode = "bundle" if args.bundle_unmapped else "strip"

    with zipfile.ZipFile(args.export_zip, "r") as zf:
        names = zf.namelist()
        if MANIFEST not in names:
            die("no manifest.json in export zip")
        manifest = json.loads(zf.read(MANIFEST).decode("utf-8"))
        present = override_mod_jars(zf)

        # --- safety: refuse to run against an export we do not fully understand ---
        known = {m["filename"] for m in mapped} | {u["filename"] for u in unmapped}
        stray = sorted(set(present) - known)
        if stray:
            die("bundled override jar(s) not in mapping (refusing to ship blind):\n  " + "\n  ".join(stray))

        for m in mapped:
            if m["filename"] not in present:
                die("mapped jar absent from export overrides/mods (stale mapping or side change): %s" % m["filename"])
        for u in unmapped:
            if u["filename"] not in present:
                die("unmapped jar absent from export overrides/mods: %s" % u["filename"])

        files = manifest.get("files", [])
        existing_pids = {f.get("projectID") for f in files}
        base_count = len(files)

        # --- append CF manifest references for the mapped mods ---
        added = []
        for m in mapped:
            if m["projectID"] in existing_pids:
                die("projectID %s already in manifest (duplicate): %s" % (m["projectID"], m["filename"]))
            files.append({"projectID": m["projectID"], "fileID": m["fileID"], "required": True})
            existing_pids.add(m["projectID"])
            added.append(m["filename"])
        manifest["files"] = files

        # --- manifest metadata ---
        manifest["name"] = mapping["manifest"].get("name", manifest.get("name", ""))
        manifest["version"] = mapping["manifest"].get("version", manifest.get("version", ""))
        manifest["author"] = mapping["manifest"].get("author", manifest.get("author", ""))

        # --- decide which override jars to drop ---
        drop = {present[m["filename"]] for m in mapped}          # mapped jars: always dropped
        kept_unmapped = []
        for u in unmapped:
            if mode == "strip":
                drop.add(present[u["filename"]])
            else:
                kept_unmapped.append(u["filename"])

        # --- write output zip ---
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as out:
            for item in zf.infolist():
                if item.filename in drop:
                    continue
                if item.filename == MANIFEST:
                    out.writestr(item, json.dumps(manifest, indent=2))
                else:
                    out.writestr(item, zf.read(item.filename))

    # --- sibling release-notes file, so the paste text ships beside the zip ---
    # version comes from cf_mapping.json manifest.version, applied to the
    # manifest above; this is the same value the zip carries.
    version = manifest.get("version", "")
    notes_out = notes_path_for(args.output)
    root = find_pack_root(os.path.dirname(os.path.abspath(__file__)))
    changelog = os.path.join(root, "CHANGELOG.md") if root else None
    notes = extract_release_notes(changelog, version) if changelog else None

    if notes:
        with open(notes_out, "w", encoding="utf-8") as fh:
            fh.write(notes)
    else:
        where = changelog or "(CHANGELOG.md not found: no pack.toml above this script)"
        sys.stderr.write(
            "\n" + "!" * 72 + "\n"
            "WARNING: NO RELEASE NOTES WRITTEN.\n"
            "  Looked for a '## %s' section with a fenced block in:\n"
            "    %s\n"
            "  The zip is complete and usable. Either add that section to\n"
            "  CHANGELOG.md and re-run, or write the CurseForge file description\n"
            "  by hand.\n"
            "  Deliberately NOT writing a placeholder: an empty or templated notes\n"
            "  file is exactly the thing that gets pasted into CurseForge by\n"
            "  mistake.\n" % (version, where)
            + "!" * 72 + "\n\n"
        )

    # --- summary ---
    print("cf_export_convert: mode=%s" % mode)
    print("  input : %s" % args.export_zip)
    print("  output: %s" % args.output)
    print("  notes : %s" % (notes_out if notes else "NOT WRITTEN (see warning above)"))
    print("  manifest files: %d -> %d (added %d CF references)" % (base_count, len(files), len(added)))
    print("  mapped jars removed from overrides: %d" % len(drop_mapped(mapped, present)))
    if mode == "strip":
        print("  unmapped stripped: %s" % ", ".join(u["filename"] for u in unmapped))
    else:
        print("  unmapped kept bundled (private zip): %s" % ", ".join(kept_unmapped))


def drop_mapped(mapped, present):
    return [m["filename"] for m in mapped if m["filename"] in present]


if __name__ == "__main__":
    main()
