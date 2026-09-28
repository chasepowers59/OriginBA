#!/usr/bin/env python3
"""Print one viewer.diagrams.net lightbox URL per page of a .drawio file (read-only preview, no
install, nothing uploaded: the diagram travels in the URL fragment and is decoded in the browser).

    python3 viewer_urls.py name.drawio            # one URL per line, in page order
    python3 viewer_urls.py name.drawio --editor   # app.diagrams.net #create= URLs instead (editable)

Encoding is draw.io's own: deflate-raw of the URI-encoded XML, base64, URI-encoded again. Measured
2026-09-28: a URL built here loaded a page that the Node-built one did not (same XML), so this is the
builder the skill uses for previews.
"""
from __future__ import annotations

import base64
import json
import re
import sys
import urllib.parse
import zlib


def encode(xml: str) -> str:
    enc = urllib.parse.quote(xml, safe="~()*!.'")   # encodeURIComponent
    raw = zlib.compress(enc.encode())[2:-4]           # deflateRaw (strip the zlib header and checksum)
    return base64.b64encode(raw).decode()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__); return 1
    text = open(sys.argv[1], encoding="utf-8").read()
    editor = "--editor" in sys.argv
    pages = re.findall(r'<diagram\b([^>]*)>([\s\S]*?)</diagram>', text)
    if not pages:
        print("no <diagram> pages", file=sys.stderr); return 1
    for attrs, model in pages:
        m = re.search(r'name="([^"]*)"', attrs); name = m.group(1) if m else "diagram"
        if editor:
            one = f'<mxfile><diagram id="p" name="{name}">{model}</diagram></mxfile>'
            payload = urllib.parse.quote(json.dumps({"type": "xml", "compressed": True, "data": encode(one)}), safe="")
            print("https://app.diagrams.net/?grid=0&pv=0&border=10&edit=_blank#create=" + payload)
        else:
            print("https://viewer.diagrams.net/?lightbox=1&nav=1&title=" + urllib.parse.quote(name) + "#R" + urllib.parse.quote(encode(model), safe=""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
