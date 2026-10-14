import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {Hero} from '../entities/Hero';
import type {HeroRepository} from '../repositories/HeroRepository';

@injectable()
export class GetHeroesUseCase {
  constructor(
    @inject(TYPES.HeroRepository)
    private readonly heroRepository: HeroRepository,
  ) {}

  execute(): Promise<Hero[]> {
    return this.heroRepository.getHeroes();
  }
}
