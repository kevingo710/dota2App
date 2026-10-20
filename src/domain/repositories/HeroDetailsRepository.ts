import type {HeroDetails} from '../entities/HeroDetails';

export interface HeroDetailsRepository {
  getHeroDetails(heroId: number): Promise<HeroDetails>;
}
