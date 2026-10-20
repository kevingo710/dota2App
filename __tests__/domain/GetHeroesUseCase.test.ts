import 'reflect-metadata';
import {GetHeroesUseCase} from '../../src/domain/usecases/GetHeroesUseCase';
import type {HeroRepository} from '../../src/domain/repositories/HeroRepository';

describe('GetHeroesUseCase', () => {
  it('returns heroes from the repository', async () => {
    const heroes = [
      {
        id: 1,
        name: 'Anti-Mage',
        picture: 'url',
        primaryAttr: 'agi' as const,
        attackType: 'Melee' as const,
        roles: ['Carry'],
      },
    ];
    const repository: HeroRepository = {
      getHeroes: jest.fn().mockResolvedValue(heroes),
    };

    await expect(new GetHeroesUseCase(repository).execute()).resolves.toBe(
      heroes,
    );
  });
});
