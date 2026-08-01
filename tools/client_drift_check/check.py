#!/usr/bin/env python3
"""client_drift_check: does this client instance still match the LIVE pack?

Compares a client instance's mods/ directory against the packwiz manifest served
from GitHub Pages, and for anything the instance has that the pack does not,
decides whether the FML handshake will reject the client.

Why this exists: removing a client-visible mod from the pack does not remove it
from a CurseForge-app instance, because the CF app does not live-sync. If that
mod registers a network channel or content registry entries and does not relax
displayTest, the server rejects the client outright with "Client has mods that
are missing on server". That is a lockout, not staleness.

Deliberately reads the LIVE pack, not the local clone: the clone is routinely
ahead of what clients actually sync from.

Usage:
    python3 check.py "/path/to/instance/mods"
    python3 check.py "/path/to/instance/mods" --pack-url <url to pack.toml>

Exit codes:
    0  instance matches the pack, or the only extras are cosmetic
    1  at least one extra jar WILL BLOCK the handshake
    2  usage error, or the live pack could not be read

stdlib only (Python 3), consistent with cf_export_convert.
"""

import argparse
import concurrent.futures
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

DEFAULT_PACK_URL = "https://stickman112.github.io/devgru-mc-pack/pack.toml"

# Signals that a mod participates in the handshake at all.
CHANNEL_TOKENS = (b"SimpleChannel", b"ChannelBuilder", b"NetworkRegistry",
                  b"registerMessage", b"SimpleImpl")
REGISTRY_TOKENS = (b"DeferredRegister", b"ForgeRegistries", b"RegisterEvent",
                   b"IForgeRegistry")
# displayTest values that tell Forge not to enforce presence/version match.
RELAXED_DISPLAY_TEST = ("IGNORE_ALL_VERSION", "IGNORE_SERVER_VERSION")


def fetch(url, timeout=30):
    """GET with a cache-buster, since GitHub Pages serves stale content for
    tens of seconds after a push and the delay is variable."""
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        url + sep + "cb=" + str(int(time.time())),
        headers={"Cache-Control": "no-cache", "User-Agent": "client_drift_check"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def load_live_pack(pack_url):
    """Return {filename: side} for every mod in the live pack."""
    base = pack_url.rsplit("/", 1)[0]
    pack = fetch(pack_url)

    m = re.search(r'^\s*file\s*=\s*"([^"]+)"', pack, re.M)
    if not m:
        raise RuntimeError("no [index] file entry in pack.toml")
    index = fetch(base + "/" + m.group(1))

    metas = re.findall(r'^\s*file\s*=\s*"(mods/[^"]+\.pw\.toml)"', index, re.M)
    if not metas:
        raise RuntimeError("no mods/*.pw.toml entries in index.toml")

    def one(rel):
        body = fetch(base + "/" + rel)
        fn = re.search(r'^\s*filename\s*=\s*"([^"]+)"', body, re.M)
        sd = re.search(r'^\s*side\s*=\s*"([^"]+)"', body, re.M)
        # packwiz omits side when it is "both"
        return (fn.group(1) if fn else None, sd.group(1) if sd else "both")

    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for fn, side in pool.map(one, metas):
            if fn:
                out[fn] = side
    return out


def inspect_jar(path):
    """Return (has_channel, has_registry, display_test, mod_id)."""
    has_channel = has_registry = False
    display_test = None
    mod_id = None
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return (False, False, None, None)
    with z:
        try:
            raw = z.read("META-INF/mods.toml").decode("utf-8", "replace")
            m = re.search(r'^\s*modId\s*=\s*"?([A-Za-z0-9_\-]+)"?', raw, re.M)
            mod_id = m.group(1) if m else None
            m = re.search(r'^\s*displayTest\s*=\s*"([^"]+)"', raw, re.M)
            display_test = m.group(1) if m else None
        except KeyError:
            pass  # not a Forge mod (plain library jar)
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            try:
                data = z.read(name)
            except Exception:
                continue
            if not has_channel and any(t in data for t in CHANNEL_TOKENS):
                has_channel = True
            if not has_registry and any(t in data for t in REGISTRY_TOKENS):
                has_registry = True
            if has_channel and has_registry:
                break
    return (has_channel, has_registry, display_test, mod_id)


def classify(has_channel, has_registry, display_test, mod_id):
    if mod_id is None:
        return ("cosmetic", "no mods.toml, not a Forge mod")
    if not (has_channel or has_registry):
        return ("cosmetic", "registers no channel and no registry entries")
    if display_test in RELAXED_DISPLAY_TEST:
        return ("cosmetic", "displayTest=%s relaxes the check" % display_test)
    shown = display_test or "absent -> MATCH_VERSION default"
    what = []
    if has_channel:
        what.append("network channel")
    if has_registry:
        what.append("content registry")
    return ("WILL BLOCK", "registers %s, displayTest %s" % (" and ".join(what), shown))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mods_dir", help="client instance mods directory (CF app or Prism)")
    ap.add_argument("--pack-url", default=DEFAULT_PACK_URL,
                    help="live pack.toml URL (default: the DEVGRU MC pack)")
    args = ap.parse_args()

    if not os.path.isdir(args.mods_dir):
        print("ERROR: not a directory: %s" % args.mods_dir, file=sys.stderr)
        return 2

    on_disk = sorted(f for f in os.listdir(args.mods_dir) if f.endswith(".jar"))
    print("instance : %s" % args.mods_dir)
    print("  jars on disk (.jar anchored): %d" % len(on_disk))

    try:
        live = load_live_pack(args.pack_url)
    except (urllib.error.URLError, RuntimeError, OSError) as exc:
        print("ERROR: could not read the live pack: %s" % exc, file=sys.stderr)
        return 2

    expected = {fn for fn, side in live.items() if side in ("both", "client")}
    print("live pack: %s" % args.pack_url)
    print("  total entries %d | expected client-side %d" % (len(live), len(expected)))

    extras = [f for f in on_disk if f not in expected]
    missing = sorted(expected - set(on_disk))

    print()
    print("EXTRA in instance, not in pack : %d" % len(extras))
    print("MISSING from instance          : %d" % len(missing))

    blocking = []
    if extras:
        print()
        print("=== extras, classified ===")
        for f in extras:
            hc, hr, dt, mid = inspect_jar(os.path.join(args.mods_dir, f))
            verdict, why = classify(hc, hr, dt, mid)
            if verdict == "WILL BLOCK":
                blocking.append((f, mid))
            print("  [%-10s] %-52s %s" % (verdict, f, why))

    if missing:
        print()
        print("=== missing from the instance ===")
        for f in missing:
            print("  %s" % f)
        print()
        print("  NOTE: a missing jar is NOT a lockout on its own, and most are not.")
        print("        A missing mod only blocks if it registers a network channel or")
        print("        content registry entries AND does not relax displayTest, in")
        print("        which case the server rejects with 'Server has additional mods")
        print("        that may be needed on the client'. A missing cosmetic or")
        print("        client-only mod just means absent content, not a rejection.")
        print("        These cannot be classified here: the jar is not present to read,")
        print("        and a metadata:curseforge pin carries no download URL.")

    print()
    if blocking:
        print("RESULT: %d extra jar(s) WILL BLOCK the handshake." % len(blocking))
        print("        Affected mod ids: %s"
              % ", ".join(sorted(m or "?" for _, m in blocking)))
        print("        CF-app clients in this state are LOCKED OUT, not merely stale.")
        print("        The CF republish is BLOCKING until this is resolved.")
        return 1
    if extras or missing:
        print("RESULT: instance differs from the pack, but nothing would block the handshake.")
        return 0
    print("RESULT: instance matches the live pack exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
