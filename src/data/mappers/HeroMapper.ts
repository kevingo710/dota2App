import type {Hero} from '../../domain/entities/Hero';
import type {HeroResponse} from '../models/HeroResponse';

const NPC_PREFIX = 'npc_dota_hero_';

const HERO_IMAGES_CDN =
  'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes';

// npc_dota_hero_<name> -> <cdn>/<name>.png (e.g. "shadow_shaman", "keeper_of_the_light").
const pictureFromNpcName = (npcName: string): string =>
  npcName.startsWith(NPC_PREFIX)
    ? `${HERO_IMAGES_CDN}/${npcName.slice(NPC_PREFIX.length)}.png`
    : '';

export const toHero = ({
  id,
  localized_name,
  name,
  primary_attr,
  attack_type,
  roles,
}: HeroResponse): Hero => ({
  id,
  name: localized_name,
  picture: pictureFromNpcName(name),
  primaryAttr: primary_attr,
  attackType: attack_type,
  roles: roles ?? [],
});

export const toHeroes = (heroes: HeroResponse[]): Hero[] => heroes.map(toHero);
