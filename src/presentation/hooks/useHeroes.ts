import {useQuery} from '@tanstack/react-query';
import {TYPES} from '../../core/di/types';
import {useInjection} from '../../core/di/DIContext';
import type {GetHeroesUseCase} from '../../domain/usecases/GetHeroesUseCase';
import {heroQueryKeys} from '../queries/heroQueryKeys';

export const useHeroes = () => {
  const getHeroes = useInjection<GetHeroesUseCase>(TYPES.GetHeroesUseCase);
  const {data, isLoading, error, refetch} = useQuery({
    queryKey: heroQueryKeys.all,
    queryFn: () => getHeroes.execute(),
  });

  return {heroes: data ?? [], isLoading, error, refetch};
};
