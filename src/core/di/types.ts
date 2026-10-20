export const TYPES = {
  HttpClient: Symbol.for('HttpClient'),
  HeroRemoteDataSource: Symbol.for('HeroRemoteDataSource'),
  HeroRepository: Symbol.for('HeroRepository'),
  HeroDetailsRemoteDataSource: Symbol.for('HeroDetailsRemoteDataSource'),
  HeroDetailsRepository: Symbol.for('HeroDetailsRepository'),
  GetHeroesUseCase: Symbol.for('GetHeroesUseCase'),
  GetHeroDetailsUseCase: Symbol.for('GetHeroDetailsUseCase'),
} as const;
