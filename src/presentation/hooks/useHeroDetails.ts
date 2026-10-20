import {useQuery} from '@tanstack/react-query';
import {TYPES} from '../../core/di/types';
import {useInjection} from '../../core/di/DIContext';
import type {GetHeroDetailsUseCase} from '../../domain/usecases/GetHeroDetailsUseCase';
import {heroQueryKeys} from '../queries/heroQueryKeys';

export const useHeroDetails = (heroId: number) => {
  const getHeroDetails = useInjection<GetHeroDetailsUseCase>(
    TYPES.GetHeroDetailsUseCase,
  );

  const {data, isLoading, error, refetch, isRefetching} = useQuery({
    queryKey: heroQueryKeys.details(heroId),
    queryFn: () => getHeroDetails.execute(heroId),
    enabled: Number.isFinite(heroId) && heroId > 0,
  });

  return {details: data, isLoading, error, refetch, isRefetching};
};
