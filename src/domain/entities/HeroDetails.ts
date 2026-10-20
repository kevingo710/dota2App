export interface HeroAbility {
  id: number;
  name: string;
  displayName: string;
  description: string;
  lore: string;
  icon: string;
  isUltimate: boolean;
  cooldown: string;
  manaCost: string;
}

export interface HeroStats {
  strength: number;
  strengthGain: number;
  agility: number;
  agilityGain: number;
  intelligence: number;
  intelligenceGain: number;
  damage: string;
  armor: string;
  movementSpeed: number;
  attackRange: number;
  attackRate: number;
  magicResistance: number;
  maxHealth: number;
  healthRegen: number;
  maxMana: number;
  manaRegen: number;
  sightRangeDay: number;
  sightRangeNight: number;
}

export interface HeroDetails {
  id: number;
  name: string;
  picture: string;
  lore: string;
  hype: string;
  complexity: number;
  stats: HeroStats;
  abilities: HeroAbility[];
}
