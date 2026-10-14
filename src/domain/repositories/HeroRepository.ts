import type {Hero} from '../entities/Hero';

export interface HeroRepository {
  getHeroes(): Promise<Hero[]>;
}
