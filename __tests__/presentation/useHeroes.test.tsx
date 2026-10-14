import 'reflect-metadata';
import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {createContainer} from '../../src/core/di/container';
import {DIProvider} from '../../src/core/di/DIContext';
import {TYPES} from '../../src/core/di/types';
import type {HeroRepository} from '../../src/domain/repositories/HeroRepository';
import {useHeroes} from '../../src/presentation/hooks/useHeroes';

test('useHeroes loads heroes through the injected use case', async () => {
  const heroes = [{id: 1, name: 'Anti-Mage', picture: 'url'}];
  const repository: HeroRepository = {
    getHeroes: jest.fn().mockResolvedValue(heroes),
  };
  const container = createContainer();
  container
    .rebind<HeroRepository>(TYPES.HeroRepository)
    .toConstantValue(repository);
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false, gcTime: Infinity}},
  });

  let result: ReturnType<typeof useHeroes> | undefined;
  const Probe = () => {
    result = useHeroes();
    return null;
  };

  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;
  await ReactTestRenderer.act(async () => {
    renderer = ReactTestRenderer.create(
      <QueryClientProvider client={queryClient}>
        <DIProvider container={container}>
          <Probe />
        </DIProvider>
      </QueryClientProvider>,
    );
  });

  for (let i = 0; i < 20 && result?.isLoading; i++) {
    await ReactTestRenderer.act(
      () => new Promise<void>(resolve => setTimeout(resolve, 0)),
    );
  }

  expect(result?.heroes).toEqual(heroes);
  expect(result?.isLoading).toBe(false);
  expect(repository.getHeroes).toHaveBeenCalledTimes(1);

  await ReactTestRenderer.act(async () => renderer?.unmount());
  queryClient.clear();
});
