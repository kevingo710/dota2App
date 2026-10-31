import {heroDataUrl} from '../../src/data/datasources/heroDataUrl.web';

describe('heroDataUrl (web)', () => {
  it('points at the static snapshot file for a hero', () => {
    expect(heroDataUrl(1)).toBe('data/heroes/1.json');
  });

  it('uses the hero id in the file name', () => {
    expect(heroDataUrl(129)).toBe('data/heroes/129.json');
  });

  it('is relative: no leading slash and no host', () => {
    const url = heroDataUrl(1);
    expect(url.startsWith('/')).toBe(false);
    expect(url.startsWith('http')).toBe(false);
  });
});
