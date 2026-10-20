import type {ValveHeroDataResponse} from '../models/ValveHeroDataResponse';

export interface HeroDetailsRemoteDataSource {
  fetchHeroDetails(heroId: number): Promise<ValveHeroDataResponse>;
}
