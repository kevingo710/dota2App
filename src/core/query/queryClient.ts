import {AppState, Platform} from 'react-native';
import type {AppStateStatus} from 'react-native';
import {focusManager, QueryClient} from '@tanstack/react-query';

// React Native has no window focus events; refetch stale queries when the app returns to the foreground.
focusManager.setEventListener(handleFocus => {
  const subscription = AppState.addEventListener(
    'change',
    (status: AppStateStatus) => {
      if (Platform.OS !== 'web') {
        handleFocus(status === 'active');
      }
    },
  );
  return () => subscription.remove();
});

export const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: 2,
      },
    },
  });

export const queryClient = createQueryClient();
