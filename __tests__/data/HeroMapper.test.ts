import {toHeroes} from '../../src/data/mappers/HeroMapper';
import type {HeroResponse} from '../../src/data/models/HeroResponse';

const response = (id: number, localized_name: string, name: string) =>
  ({id, localized_name, name} as HeroResponse);

describe('HeroMapper.toHeroes', () => {
  it('builds picture urls from single and multi-word npc names', () => {
    expect(
      toHeroes([
        response(1, 'Anti-Mage', 'npc_dota_hero_antimage'),
        response(27, 'Shadow Shaman', 'npc_dota_hero_shadow_shaman'),
      ]),
    ).toEqual([
      {
        id: 1,
        name: 'Anti-Mage',
        picture:
          'https://api.opendota.com/apps/dota2/images/heroes/antimage_full.png',
      },
      {
        id: 27,
        name: 'Shadow Shaman',
        picture:
          'https://api.opendota.com/apps/dota2/images/heroes/shadow_shaman_full.png',
      },
    ]);
  });

  it('excludes Dawnbreaker', () => {
    expect(
      toHeroes([response(135, 'Dawnbreaker', 'npc_dota_hero_dawnbreaker')]),
    ).toEqual([]);
  });
});
