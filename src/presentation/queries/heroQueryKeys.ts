export const heroQueryKeys = {
  all: ['heroes'] as const,
  details: (heroId: number) => ['heroes', 'details', heroId] as const,
};
