// Valve's herodata endpoint sends no CORS headers, so the web build reads the
// snapshot that scripts/snapshot-herodata.mjs writes next to the app.
// Relative on purpose: it resolves against the page URL (/dota2App/app/).
export const heroDataUrl = (heroId: number): string =>
  `data/heroes/${heroId}.json`;
