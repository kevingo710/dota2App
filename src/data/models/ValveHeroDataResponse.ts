export interface ValveHeroDataResponse {
  result: {
    data: {
      heroes: ValveHero[];
    };
  };
}

export interface ValveHero {
  id: number;
  name: string;
  name_loc: string;
  bio_loc: string;
  hype_loc: string;
  str_base: number;
  str_gain: number;
  agi_base: number;
  agi_gain: number;
  int_base: number;
  int_gain: number;
  primary_attr: number;
  complexity: number;
  damage_min: number;
  damage_max: number;
  armor: number;
  attack_rate: number;
  attack_range: number;
  magic_resistance: number;
  movement_speed: number;
  sight_range_day: number;
  sight_range_night: number;
  max_health: number;
  health_regen: number;
  max_mana: number;
  mana_regen: number;
  abilities: ValveAbility[];
}

export interface ValveAbility {
  id: number;
  name: string;
  name_loc: string;
  desc_loc: string;
  lore_loc?: string | null;
  type: number;
  cooldowns: number[];
  mana_costs: number[];
  ability_is_innate: boolean;
  is_item: boolean;
  special_values?: ValveSpecialValue[];
}

export interface ValveSpecialValue {
  name: string;
  values_float?: number[];
  values?: number[];
  is_percentage?: boolean;
}
