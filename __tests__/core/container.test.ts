import 'reflect-metadata';
import {createContainer} from '../../src/core/di/container';
import {TYPES} from '../../src/core/di/types';
import type {HttpClient} from '../../src/infrastructure/http/HttpClient';
import {GetHeroesUseCase} from '../../src/domain/usecases/GetHeroesUseCase';

describe('DI container', () => {
  it('wires GetHeroesUseCase through repository, data source and HttpClient', async () => {
    const container = createContainer();
    const http: HttpClient = {
      get: jest
        .fn()
        .mockResolvedValue([
          {id: 1, localized_name: 'Anti-Mage', name: 'npc_dota_hero_antimage'},
        ]),
    };
    container.rebind<HttpClient>(TYPES.HttpClient).toConstantValue(http);

    const useCase = container.get<GetHeroesUseCase>(TYPES.GetHeroesUseCase);

    expect(useCase).toBeInstanceOf(GetHeroesUseCase);
    await expect(useCase.execute()).resolves.toEqual([
      expect.objectContaining({id: 1, name: 'Anti-Mage'}),
    ]);
    expect(http.get).toHaveBeenCalledWith(
      'https://api.opendota.com/api/heroes',
    );
  });
});
