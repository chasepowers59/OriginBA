#!/usr/bin/env node
// Headless draw.io passes for Origin visuals, using the official @drawio/mcp package's own
// engines (no draw.io Desktop needed):
//
//   node drawio_pass.mjs route  in.drawio out.drawio          libavoid: keep positions, re-route edges around boxes
//   node drawio_pass.mjs elk    in.drawio out.drawio [dir]    ELK layered re-layout (dir: vertical | horizontal)
//   node drawio_pass.mjs url    in.drawio                     print an app.diagrams.net #create URL (opens the editor)
//   node drawio_pass.mjs viewer in.drawio                     print a viewer.diagrams.net lightbox URL (read-only)
//
// Every page of the .drawio file is processed. Pages are stored uncompressed.
import { readFileSync, writeFileSync } from "fs";
import zlib from "zlib";
import { routeXml } from "@drawio/mcp/src/libavoid-pass.js";
import { layoutXml } from "@drawio/mcp/src/elk-pass.js";

const [cmd, inPath, outPath, dir] = process.argv.slice(2);
if (!cmd || !inPath) { console.error("usage: drawio_pass.mjs route|elk|url|viewer in.drawio [out.drawio] [vertical|horizontal]"); process.exit(1); }
const file = readFileSync(inPath, "utf8");
const pages = [...file.matchAll(/<diagram\b([^>]*)>([\s\S]*?)<\/diagram>/g)];
if (!pages.length) { console.error("no <diagram> pages in " + inPath); process.exit(1); }

async function transform(fn) {
  let out = file;
  for (const m of pages) {
    const model = m[2];
    if (!model.startsWith("<mxGraphModel")) { console.error("page is compressed; store pages uncompressed"); process.exit(1); }
    const next = await fn(model);
    out = out.replace(m[0], `<diagram${m[1]}>${next}</diagram>`);
  }
  writeFileSync(outPath || inPath, out);
  console.log(`wrote ${outPath || inPath} (${pages.length} page(s))`);
}

function encode(xml) { return zlib.deflateRawSync(encodeURIComponent(xml)).toString("base64"); }

if (cmd === "route") await transform((m) => routeXml(m));
else if (cmd === "elk") await transform((m) => layoutXml(m, { direction: dir || "vertical" }));
else if (cmd === "url") {
  const payload = encodeURIComponent(JSON.stringify({ type: "xml", compressed: true, data: encode(file) }));
  console.log("https://app.diagrams.net/?grid=0&pv=0&border=10&edit=_blank#create=" + payload);
} else if (cmd === "viewer") {
  console.log("https://viewer.diagrams.net/?lightbox=1&nav=1&highlight=0000ff&title=diagram#R" + encodeURIComponent(encode(pages[0][2])));
} else { console.error("unknown command " + cmd); process.exit(1); }
