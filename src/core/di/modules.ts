import {ContainerModule} from 'inversify';
import {TYPES} from './types';
import type {HttpClient} from '../../infrastructure/http/HttpClient';
import {AxiosHttpClient} from '../../infrastructure/http/AxiosHttpClient';
import type {HeroRemoteDataSource} from '../../data/datasources/HeroRemoteDataSource';
import {OpenDotaHeroRemoteDataSource} from '../../data/datasources/OpenDotaHeroRemoteDataSource';
import type {HeroRepository} from '../../domain/repositories/HeroRepository';
import {HeroRepositoryImpl} from '../../data/repositories/HeroRepositoryImpl';
import {GetHeroesUseCase} from '../../domain/usecases/GetHeroesUseCase';
import type {HeroDetailsRemoteDataSource} from '../../data/datasources/HeroDetailsRemoteDataSource';
import {ValveHeroDetailsRemoteDataSource} from '../../data/datasources/ValveHeroDetailsRemoteDataSource';
import type {HeroDetailsRepository} from '../../domain/repositories/HeroDetailsRepository';
import {HeroDetailsRepositoryImpl} from '../../data/repositories/HeroDetailsRepositoryImpl';
import {GetHeroDetailsUseCase} from '../../domain/usecases/GetHeroDetailsUseCase';

export const infrastructureModule = new ContainerModule(({bind}) => {
  bind<HttpClient>(TYPES.HttpClient).to(AxiosHttpClient).inSingletonScope();
});

export const dataModule = new ContainerModule(({bind}) => {
  bind<HeroRemoteDataSource>(TYPES.HeroRemoteDataSource)
    .to(OpenDotaHeroRemoteDataSource)
    .inSingletonScope();
  bind<HeroRepository>(TYPES.HeroRepository)
    .to(HeroRepositoryImpl)
    .inSingletonScope();
  bind<HeroDetailsRemoteDataSource>(TYPES.HeroDetailsRemoteDataSource)
    .to(ValveHeroDetailsRemoteDataSource)
    .inSingletonScope();
  bind<HeroDetailsRepository>(TYPES.HeroDetailsRepository)
    .to(HeroDetailsRepositoryImpl)
    .inSingletonScope();
});

export const domainModule = new ContainerModule(({bind}) => {
  bind<GetHeroesUseCase>(TYPES.GetHeroesUseCase).to(GetHeroesUseCase);
  bind<GetHeroDetailsUseCase>(TYPES.GetHeroDetailsUseCase).to(
    GetHeroDetailsUseCase,
  );
});
