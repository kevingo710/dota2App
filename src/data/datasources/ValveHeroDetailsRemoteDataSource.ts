import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {HttpClient} from '../../infrastructure/http/HttpClient';
import type {ValveHeroDataResponse} from '../models/ValveHeroDataResponse';
import type {HeroDetailsRemoteDataSource} from './HeroDetailsRemoteDataSource';
import {heroDataUrl} from './heroDataUrl';

@injectable()
export class ValveHeroDetailsRemoteDataSource
  implements HeroDetailsRemoteDataSource
{
  constructor(@inject(TYPES.HttpClient) private readonly http: HttpClient) {}

  fetchHeroDetails(heroId: number): Promise<ValveHeroDataResponse> {
    return this.http.get<ValveHeroDataResponse>(heroDataUrl(heroId));
  }
}
