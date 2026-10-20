import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {HeroDetails} from '../../domain/entities/HeroDetails';
import type {HeroDetailsRepository} from '../../domain/repositories/HeroDetailsRepository';
import type {HeroDetailsRemoteDataSource} from '../datasources/HeroDetailsRemoteDataSource';
import {toHeroDetails} from '../mappers/HeroDetailsMapper';

@injectable()
export class HeroDetailsRepositoryImpl implements HeroDetailsRepository {
  constructor(
    @inject(TYPES.HeroDetailsRemoteDataSource)
    private readonly remoteDataSource: HeroDetailsRemoteDataSource,
  ) {}

  async getHeroDetails(heroId: number): Promise<HeroDetails> {
    const response = await this.remoteDataSource.fetchHeroDetails(heroId);
    const hero = response.result?.data?.heroes?.[0];

    if (!hero) {
      throw new Error(`No details found for hero ${heroId}`);
    }

    return toHeroDetails(hero);
  }
}
