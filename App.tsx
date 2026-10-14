import React from 'react';
import {DefaultTheme, NavigationContainer} from '@react-navigation/native';
import type {Theme} from '@react-navigation/native';
import colors from './src/presentation/theme/colors';
import Navigator from './src/presentation/navigation/Navigator';
import {DIProvider} from './src/core/di/DIContext';
import {container} from './src/core/di/container';
import {QueryClientProvider} from '@tanstack/react-query';
import {queryClient} from './src/core/query/queryClient';

// import {ENV_VAR} from '@env';
// import {API_EV} from '@env';

const MyTheme: Theme = {
  ...DefaultTheme,
  colors: {
    primary: colors.orange,
    background: colors.darkBlue,
    card: 'rgb(255, 255, 255)',
    text: colors.gray,
    border: colors.darkBlue,
    notification: colors.orange,
  },
};
const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <DIProvider container={container}>
        <NavigationContainer theme={MyTheme}>
          <Navigator />
        </NavigationContainer>
      </DIProvider>
    </QueryClientProvider>
  );
};

export default App;
