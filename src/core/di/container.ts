import {Container} from 'inversify';
import {dataModule, domainModule, infrastructureModule} from './modules';

export const createContainer = (): Container => {
  const container = new Container();
  container.load(infrastructureModule, dataModule, domainModule);
  return container;
};

export const container = createContainer();
