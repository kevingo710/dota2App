#!/usr/bin/env node
// Snapshot Valve's per-hero data for the web build.
//
// Why: https://www.dota2.com/datafeed/herodata sends no CORS headers, so a
// browser cannot call it. The native app still does; the web build reads
// <outDir>/data/heroes/<id>.json instead (src/data/datasources/heroDataUrl.web.ts).
// Run it after the web build, into the same output directory.
//
// Usage: node scripts/snapshot-herodata.mjs <outDir>   (e.g. dist/web)
import {mkdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';

const HERO_STATS_URL = 'https://api.opendota.com/api/heroStats';
// Same URL as the native src/data/datasources/heroDataUrl.ts.
const heroDataUrl = id =>
  `https://www.dota2.com/datafeed/herodata?language=english&hero_id=${id}`;
const IN_FLIGHT = 4;
const RETRIES = 3;

const outDir = process.argv[2];
if (!outDir) {
  console.error('usage: node scripts/snapshot-herodata.mjs <outDir>');
  process.exit(2);
}

const fetchText = async url => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return res.text();
};

const withRetries = async (url, label) => {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetchText(url);
    } catch (error) {
      if (attempt === RETRIES) {
        throw error;
      }
      console.error(`${label}: ${error.message}, retrying`);
      await new Promise(resolve => setTimeout(resolve, 1000 * 2 ** attempt));
    }
  }
};

const ids = JSON.parse(await withRetries(HERO_STATS_URL, 'heroStats')).map(
  hero => hero.id,
);
const dir = join(outDir, 'data', 'heroes');
await mkdir(dir, {recursive: true});

const queue = [...ids];
const failed = [];
let written = 0;

const worker = async () => {
  for (let id = queue.shift(); id !== undefined; id = queue.shift()) {
    try {
      const body = await withRetries(heroDataUrl(id), `hero ${id}`);
      await writeFile(join(dir, `${id}.json`), body);
      written++;
    } catch (error) {
      failed.push(id);
      console.error(`hero ${id}: ${error.message}`);
    }
  }
};

await Promise.all(Array.from({length: IN_FLIGHT}, worker));

console.log(`wrote ${written} hero files to ${dir}`);
if (failed.length) {
  console.error(`failed hero ids: ${failed.sort((a, b) => a - b).join(', ')}`);
  process.exit(1);
}
