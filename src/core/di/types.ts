export const TYPES = {
  HttpClient: Symbol.for('HttpClient'),
  HeroRemoteDataSource: Symbol.for('HeroRemoteDataSource'),
  HeroRepository: Symbol.for('HeroRepository'),
  GetHeroesUseCase: Symbol.for('GetHeroesUseCase'),
} as const;
