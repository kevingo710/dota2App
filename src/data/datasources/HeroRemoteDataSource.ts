import type {HeroResponse} from '../models/HeroResponse';

export interface HeroRemoteDataSource {
  fetchHeroes(): Promise<HeroResponse[]>;
}
