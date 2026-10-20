import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {HeroDetails} from '../entities/HeroDetails';
import type {HeroDetailsRepository} from '../repositories/HeroDetailsRepository';

@injectable()
export class GetHeroDetailsUseCase {
  constructor(
    @inject(TYPES.HeroDetailsRepository)
    private readonly heroDetailsRepository: HeroDetailsRepository,
  ) {}

  execute(heroId: number): Promise<HeroDetails> {
    return this.heroDetailsRepository.getHeroDetails(heroId);
  }
}
