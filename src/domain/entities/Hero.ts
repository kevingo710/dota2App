export type HeroAttribute = 'str' | 'agi' | 'int' | 'all';
export type HeroAttackType = 'Melee' | 'Ranged';

export interface Hero {
  id: number;
  name: string;
  picture: string;
  primaryAttr: HeroAttribute;
  attackType: HeroAttackType;
  roles: string[];
}
