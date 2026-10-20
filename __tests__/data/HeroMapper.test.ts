import {toHeroes} from '../../src/data/mappers/HeroMapper';
import {AttackType, PrimaryAttr} from '../../src/data/models/HeroResponse';
import type {HeroResponse} from '../../src/data/models/HeroResponse';

const CDN =
  'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes';

const response = (
  id: number,
  localized_name: string,
  name: string,
  primary_attr: PrimaryAttr = PrimaryAttr.Agi,
  attack_type: AttackType = AttackType.Melee,
  roles: string[] = ['Carry'],
) =>
  ({
    id,
    localized_name,
    name,
    primary_attr,
    attack_type,
    roles,
  } as HeroResponse);

describe('HeroMapper.toHeroes', () => {
  it('builds picture urls from single and multi-word npc names', () => {
    expect(
      toHeroes([
        response(1, 'Anti-Mage', 'npc_dota_hero_antimage'),
        response(
          27,
          'Shadow Shaman',
          'npc_dota_hero_shadow_shaman',
          PrimaryAttr.Int,
        ),
        response(
          90,
          'Keeper of the Light',
          'npc_dota_hero_keeper_of_the_light',
          PrimaryAttr.Int,
          AttackType.Ranged,
        ),
      ]),
    ).toEqual([
      {
        id: 1,
        name: 'Anti-Mage',
        picture: `${CDN}/antimage.png`,
        primaryAttr: PrimaryAttr.Agi,
        attackType: AttackType.Melee,
        roles: ['Carry'],
      },
      {
        id: 27,
        name: 'Shadow Shaman',
        picture: `${CDN}/shadow_shaman.png`,
        primaryAttr: PrimaryAttr.Int,
        attackType: AttackType.Melee,
        roles: ['Carry'],
      },
      {
        id: 90,
        name: 'Keeper of the Light',
        picture: `${CDN}/keeper_of_the_light.png`,
        primaryAttr: PrimaryAttr.Int,
        attackType: AttackType.Ranged,
        roles: ['Carry'],
      },
    ]);
  });

  it('includes every hero, including Dawnbreaker', () => {
    expect(
      toHeroes([
        response(
          135,
          'Dawnbreaker',
          'npc_dota_hero_dawnbreaker',
          PrimaryAttr.Str,
        ),
      ]),
    ).toEqual([
      {
        id: 135,
        name: 'Dawnbreaker',
        picture: `${CDN}/dawnbreaker.png`,
        primaryAttr: PrimaryAttr.Str,
        attackType: AttackType.Melee,
        roles: ['Carry'],
      },
    ]);
  });

  it('maps universal heroes', () => {
    expect(
      toHeroes([
        response(
          138,
          'Marci',
          'npc_dota_hero_marci',
          PrimaryAttr.All,
          AttackType.Melee,
          ['Carry', 'Support'],
        ),
      ])[0],
    ).toEqual(
      expect.objectContaining({
        primaryAttr: PrimaryAttr.All,
        roles: ['Carry', 'Support'],
      }),
    );
  });
});
