import React from 'react';
import {DefaultTheme, NavigationContainer} from '@react-navigation/native';
import type {Theme} from '@react-navigation/native';
import colors from './src/styles/colors';
import Navigator from './src/navigator/Navigator';

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
    <NavigationContainer theme={MyTheme}>
      <Navigator />
    </NavigationContainer>
  );
};

export default App;
