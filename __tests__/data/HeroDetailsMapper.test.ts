import {toHeroDetails} from '../../src/data/mappers/HeroDetailsMapper';
import type {ValveHero} from '../../src/data/models/ValveHeroDataResponse';

const hero = {
  id: 8,
  name: 'npc_dota_hero_juggernaut',
  name_loc: 'Juggernaut',
  bio_loc: 'No one has ever seen the face hidden beneath the mask.',
  hype_loc: 'In a <b>flurry of slashes</b>, Juggernaut cuts down his foes.',
  str_base: 20,
  str_gain: 2,
  agi_base: 32,
  agi_gain: 2.8,
  int_base: 14,
  int_gain: 1.4,
  primary_attr: 1,
  complexity: 1,
  damage_min: 54,
  damage_max: 56,
  armor: 5.3333335,
  attack_rate: 1.4,
  attack_range: 150,
  magic_resistance: 25,
  movement_speed: 305,
  sight_range_day: 1800,
  sight_range_night: 800,
  max_health: 560,
  health_regen: 2.5,
  max_mana: 243,
  mana_regen: 0.7,
  abilities: [
    {
      id: 5028,
      name: 'juggernaut_blade_fury',
      name_loc: 'Blade Fury',
      desc_loc:
        'Deals %blade_fury_damage_tick%s of damage and grants %immunity_resist%%% magic resistance.',
      lore_loc: "Yurnero's renowned katana techniques.",
      type: 0,
      cooldowns: [30, 26, 22, 18],
      mana_costs: [110],
      ability_is_innate: false,
      is_item: false,
      special_values: [
        {
          name: 'blade_fury_damage_tick',
          values_float: [20, 35, 50, 65],
          is_percentage: false,
        },
        {
          name: 'immunity_resist',
          values_float: [80],
          is_percentage: false,
        },
      ],
    },
    {
      id: 5032,
      name: 'juggernaut_omni_slash',
      name_loc: 'Omnislash',
      desc_loc:
        'Juggernaut leaps towards the target enemy.&#10;DISPEL TYPE: &amp; Basic Dispel.',
      lore_loc: '',
      type: 1,
      cooldowns: [120],
      mana_costs: [200],
      ability_is_innate: false,
      is_item: false,
    },
    {
      id: 9000,
      name: 'juggernaut_bladeform',
      name_loc: 'Bladeform',
      desc_loc: 'Innate passive.',
      lore_loc: '',
      type: 0,
      cooldowns: [],
      mana_costs: [],
      ability_is_innate: true,
      is_item: false,
    },
  ],
} as ValveHero;

describe('HeroDetailsMapper.toHeroDetails', () => {
  it('maps stats and rounds them', () => {
    const details = toHeroDetails(hero);

    expect(details.stats).toEqual(
      expect.objectContaining({
        strength: 20,
        strengthGain: 2,
        agility: 32,
        agilityGain: 2.8,
        intelligence: 14,
        intelligenceGain: 1.4,
        damage: '54 - 56',
        armor: '5.3',
        movementSpeed: 305,
        magicResistance: 25,
      }),
    );
  });

  it('builds the hero picture url from the npc name', () => {
    expect(toHeroDetails(hero).picture).toBe(
      'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/juggernaut.png',
    );
  });

  it('strips markup and placeholder tokens from text', () => {
    const details = toHeroDetails(hero);

    expect(details.hype).toBe(
      'In a flurry of slashes, Juggernaut cuts down his foes.',
    );
    expect(details.abilities[0].description).toBe(
      'Deals 20 / 35 / 50 / 65s of damage and grants 80% magic resistance.',
    );
  });

  it('keeps non-innate abilities and formats cooldowns', () => {
    const details = toHeroDetails(hero);

    expect(details.abilities).toHaveLength(2);
    expect(details.abilities[0]).toEqual(
      expect.objectContaining({
        displayName: 'Blade Fury',
        isUltimate: false,
        cooldown: '30 / 26 / 22 / 18s',
        manaCost: '110',
        icon: 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/abilities/juggernaut_blade_fury.png',
      }),
    );
    expect(details.abilities[1].isUltimate).toBe(true);
  });

  it('decodes html entities into text', () => {
    const details = toHeroDetails(hero);

    expect(details.abilities[1].description).toBe(
      'Juggernaut leaps towards the target enemy.\nDISPEL TYPE: & Basic Dispel.',
    );
  });
});
