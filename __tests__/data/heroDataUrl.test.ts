import {heroDataUrl} from '../../src/data/datasources/heroDataUrl';

describe('heroDataUrl (native)', () => {
  it('builds the Valve herodata url for a hero', () => {
    expect(heroDataUrl(1)).toBe(
      'https://www.dota2.com/datafeed/herodata?language=english&hero_id=1',
    );
  });

  it('interpolates the hero id into hero_id', () => {
    expect(heroDataUrl(129)).toBe(
      'https://www.dota2.com/datafeed/herodata?language=english&hero_id=129',
    );
  });
});
