const VALVE_HERO_DATA_URL = 'https://www.dota2.com/datafeed/herodata';

export const heroDataUrl = (heroId: number): string =>
  `${VALVE_HERO_DATA_URL}?language=english&hero_id=${heroId}`;
