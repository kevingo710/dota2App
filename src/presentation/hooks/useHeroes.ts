import {useCallback, useEffect, useState} from 'react';
import {TYPES} from '../../core/di/types';
import {useInjection} from '../../core/di/DIContext';
import type {Hero} from '../../domain/entities/Hero';
import type {GetHeroesUseCase} from '../../domain/usecases/GetHeroesUseCase';

export const useHeroes = () => {
  const getHeroes = useInjection<GetHeroesUseCase>(TYPES.GetHeroesUseCase);
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadHeroes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setHeroes(await getHeroes.execute());
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [getHeroes]);

  useEffect(() => {
    loadHeroes();
  }, [loadHeroes]);

  return {heroes, isLoading, error, loadHeroes};
};
