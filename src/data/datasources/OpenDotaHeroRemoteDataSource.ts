import {inject, injectable} from 'inversify';
import {TYPES} from '../../core/di/types';
import type {HttpClient} from '../../infrastructure/http/HttpClient';
import type {HeroResponse} from '../models/HeroResponse';
import type {HeroRemoteDataSource} from './HeroRemoteDataSource';

const OPEN_DOTA_API = 'https://api.opendota.com/api';

@injectable()
export class OpenDotaHeroRemoteDataSource implements HeroRemoteDataSource {
  constructor(@inject(TYPES.HttpClient) private readonly http: HttpClient) {}

  fetchHeroes(): Promise<HeroResponse[]> {
    return this.http.get<HeroResponse[]>(`${OPEN_DOTA_API}/heroes`);
  }
}
