import {toHeroes} from '../../src/data/mappers/HeroMapper';
import type {HeroResponse} from '../../src/data/models/HeroResponse';

const CDN =
  'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes';

const response = (id: number, localized_name: string, name: string) =>
  ({id, localized_name, name} as HeroResponse);

describe('HeroMapper.toHeroes', () => {
  it('builds picture urls from single and multi-word npc names', () => {
    expect(
      toHeroes([
        response(1, 'Anti-Mage', 'npc_dota_hero_antimage'),
        response(27, 'Shadow Shaman', 'npc_dota_hero_shadow_shaman'),
        response(
          90,
          'Keeper of the Light',
          'npc_dota_hero_keeper_of_the_light',
        ),
      ]),
    ).toEqual([
      {
        id: 1,
        name: 'Anti-Mage',
        picture: `${CDN}/antimage.png`,
      },
      {
        id: 27,
        name: 'Shadow Shaman',
        picture: `${CDN}/shadow_shaman.png`,
      },
      {
        id: 90,
        name: 'Keeper of the Light',
        picture: `${CDN}/keeper_of_the_light.png`,
      },
    ]);
  });

  it('excludes Dawnbreaker', () => {
    expect(
      toHeroes([response(135, 'Dawnbreaker', 'npc_dota_hero_dawnbreaker')]),
    ).toEqual([]);
  });
});
