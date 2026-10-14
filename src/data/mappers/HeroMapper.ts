import type {Hero} from '../../domain/entities/Hero';
import type {HeroResponse} from '../models/HeroResponse';

const EXCLUDED_HEROES = ['Dawnbreaker'];

const heroImageUrl = (npcName: string) =>
  `https://api.opendota.com/apps/dota2/images/heroes/${npcName}_full.png`;

// npc_dota_hero_<name> -> <name>; names may contain one underscore (e.g. "shadow_shaman").
const pictureFromNpcName = (npcName: string): string => {
  const nameParts = npcName.split('_');
  if (nameParts.length === 4) {
    return heroImageUrl(nameParts.slice(-1).join());
  }
  if (nameParts.length === 5) {
    return heroImageUrl(nameParts.slice(-2).join('_'));
  }
  return '';
};

export const toHero = ({id, localized_name, name}: HeroResponse): Hero => ({
  id,
  name: localized_name,
  picture: pictureFromNpcName(name),
});

export const toHeroes = (heroes: HeroResponse[]): Hero[] =>
  heroes.map(toHero).filter(hero => !EXCLUDED_HEROES.includes(hero.name));
