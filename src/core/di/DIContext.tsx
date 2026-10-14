import React, {
  createContext,
  PropsWithChildren,
  useContext,
  useMemo,
} from 'react';
import type {Container, ServiceIdentifier} from 'inversify';
import {container as defaultContainer} from './container';

const DIContext = createContext<Container>(defaultContainer);

export const DIProvider = ({
  container,
  children,
}: PropsWithChildren<{container: Container}>) => (
  <DIContext.Provider value={container}>{children}</DIContext.Provider>
);

export const useInjection = <T,>(identifier: ServiceIdentifier<T>): T => {
  const container = useContext(DIContext);
  return useMemo(() => container.get<T>(identifier), [container, identifier]);
};
