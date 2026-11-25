import { copyFile, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, '..');
const dist = path.join(frontend, 'dist');
const htmlPath = path.join(dist, 'index.html');
const assets = path.join(dist, 'assets');
const stableName = 'cognigraph-style-check.css';

let html = await readFile(htmlPath, 'utf8');
const links = [...html.matchAll(/href="([^"]+\.css(?:\?[^\"]*)?)"/g)];
if (links.length !== 1) {
  throw new Error(`Expected exactly one CSS stylesheet link in ${htmlPath}; found ${links.length}. No CSS URL was changed.`);
}
const originalHref = links[0][1];
const pathname = new URL(originalHref, 'http://cognigraph.local').pathname;
const originalFile = path.basename(pathname);
const sourceCss = path.join(assets, originalFile);
const stableCss = path.join(assets, stableName);

await copyFile(sourceCss, stableCss);
const directory = pathname.slice(0, pathname.lastIndexOf('/') + 1) || '/assets/';
const stableHref = `${directory}${stableName}`;
html = html.replace(links[0][0], `href="${stableHref}"`);
await writeFile(htmlPath, html, 'utf8');
console.log(`CSS URL made stable: ${originalHref} -> ${stableHref}`);
console.log(`Copied ${sourceCss} -> ${stableCss}`);
