import type {
  HeroAbility,
  HeroDetails,
  HeroStats,
} from '../../domain/entities/HeroDetails';
import type {
  ValveAbility,
  ValveHero,
  ValveSpecialValue,
} from '../models/ValveHeroDataResponse';

const HEROES_CDN =
  'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes';

const ABILITIES_CDN =
  'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/abilities';

const pictureFromNpcName = (npcName: string): string =>
  npcName.startsWith('npc_dota_hero_')
    ? `${HEROES_CDN}/${npcName.slice('npc_dota_hero_'.length)}.png`
    : '';

const round = (value: number, decimals = 0): number =>
  Number.isFinite(value) ? Number(value.toFixed(decimals)) : 0;

interface SpecialValue {
  label: string;
  isPercentage: boolean;
}

const formatSpecialValue = (special: ValveSpecialValue): string =>
  Array.from(
    new Set(
      (special.values_float ?? special.values ?? [])
        .filter(value => Number.isFinite(value))
        .map(value => round(value, 2)),
    ),
  ).join(' / ');

const toSpecialValues = (
  ability: ValveAbility,
): Map<string, SpecialValue> => {
  const values = new Map<string, SpecialValue>();
  for (const special of ability.special_values ?? []) {
    if (!special.name) {
      continue;
    }
    const label = formatSpecialValue(special);
    if (label) {
      values.set(special.name.toLowerCase(), {
        label,
        isPercentage: Boolean(special.is_percentage),
      });
    }
  }
  return values;
};

const stripMarkup = (
  text?: string | null,
  specialValues?: Map<string, SpecialValue>,
): string =>
  (text ?? '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(
      /%([a-z0-9_]+)%/gi,
      (match: string, token: string, offset: number, full: string) => {
        const special = specialValues?.get(token.toLowerCase());
        if (!special) {
          return '';
        }
        const next = full.slice(offset + match.length);
        return special.isPercentage && !next.startsWith('%%')
          ? `${special.label}%`
          : special.label;
      },
    )
    .replace(/%%/g, '%')
    .replace(/&#x([0-9a-f]+);/gi, (_, code: string) =>
      String.fromCharCode(parseInt(code, 16)),
    )
    .replace(/&#(\d+);/g, (_, code: string) =>
      String.fromCharCode(Number(code)),
    )
    .replace(/&nbsp;/gi, ' ')
    .replace(/&quot;/gi, '"')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&amp;/gi, '&')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

const formatList = (values: number[], suffix: string): string => {
  const positives = values.filter(value => value > 0);
  if (!positives.length) {
    return '-';
  }
  return `${Array.from(new Set(positives)).join(' / ')}${suffix}`;
};

const toAbility = (ability: ValveAbility): HeroAbility => {
  const specialValues = toSpecialValues(ability);
  return {
    id: ability.id,
    name: ability.name,
    displayName: ability.name_loc,
    description: stripMarkup(ability.desc_loc, specialValues),
    lore: stripMarkup(ability.lore_loc, specialValues),
    icon: `${ABILITIES_CDN}/${ability.name}.png`,
    isUltimate: ability.type === 1,
    cooldown: formatList(ability.cooldowns ?? [], 's'),
    manaCost: formatList(ability.mana_costs ?? [], ''),
  };
};

const toStats = (hero: ValveHero): HeroStats => ({
  strength: round(hero.str_base),
  strengthGain: round(hero.str_gain, 1),
  agility: round(hero.agi_base),
  agilityGain: round(hero.agi_gain, 1),
  intelligence: round(hero.int_base),
  intelligenceGain: round(hero.int_gain, 1),
  damage: `${round(hero.damage_min)} - ${round(hero.damage_max)}`,
  armor: `${round(hero.armor, 1)}`,
  movementSpeed: round(hero.movement_speed),
  attackRange: round(hero.attack_range),
  attackRate: round(hero.attack_rate, 2),
  magicResistance: round(hero.magic_resistance),
  maxHealth: round(hero.max_health),
  healthRegen: round(hero.health_regen, 1),
  maxMana: round(hero.max_mana),
  manaRegen: round(hero.mana_regen, 1),
  sightRangeDay: round(hero.sight_range_day),
  sightRangeNight: round(hero.sight_range_night),
});

export const toHeroDetails = (hero: ValveHero): HeroDetails => ({
  id: hero.id,
  name: hero.name_loc,
  picture: pictureFromNpcName(hero.name),
  lore: stripMarkup(hero.bio_loc),
  hype: stripMarkup(hero.hype_loc),
  complexity: hero.complexity,
  stats: toStats(hero),
  abilities: (hero.abilities ?? [])
    .filter(ability => !ability.is_item && !ability.ability_is_innate)
    .map(toAbility),
});
