/* eslint-env jest */
import mockSafeAreaContext from 'react-native-safe-area-context/jest/mock';

jest.mock('react-native-safe-area-context', () => mockSafeAreaContext);

jest.mock('axios', () => {
  const instance = {get: jest.fn(() => Promise.resolve({data: []}))};
  return {
    __esModule: true,
    default: {create: jest.fn(() => instance)},
  };
});
