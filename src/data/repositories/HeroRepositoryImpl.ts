import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {Hero} from '../../domain/entities/Hero';
import type {HeroRepository} from '../../domain/repositories/HeroRepository';
import type {HeroRemoteDataSource} from '../datasources/HeroRemoteDataSource';
import {toHeroes} from '../mappers/HeroMapper';

@injectable()
export class HeroRepositoryImpl implements HeroRepository {
  constructor(
    @inject(TYPES.HeroRemoteDataSource)
    private readonly remoteDataSource: HeroRemoteDataSource,
  ) {}

  async getHeroes(): Promise<Hero[]> {
    return toHeroes(await this.remoteDataSource.fetchHeroes());
  }
}
