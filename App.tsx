import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/Ionicons';
import HomeScreen from './src/screens/HomeScreen';
import ExploreScreen from './src/screens/ExploreScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import {Platform} from 'react-native';
import SettingsScreen from './src/screens/SettingsScreen';
import colors from './src/styles/colors';

// import {ENV_VAR} from '@env';
// import {API_EV} from '@env';

const MyTheme = {
  dark: false,
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
  const Tab = createBottomTabNavigator();
  return (
    <NavigationContainer theme={MyTheme}>
      <Tab.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            paddingVertical: Platform.OS === 'ios' ? 20 : 0,
            height: 90,
            paddingHorizontal: 5,
            paddingTop: 0,
            backgroundColor: colors.darkBlue,
            position: 'absolute',
            borderTopWidth: 0,
          },
        }}>
        <Tab.Screen
          name="Home"
          component={HomeScreen}
          options={{
            tabBarLabel: 'Home',
            tabBarIcon: ({color, size}) => (
              <Icon name="home" color={color} size={size} />
            ),
            tabBarLabelPosition: 'beside-icon',
          }}
        />
        <Tab.Screen name="Settings" component={SettingsScreen} />
        <Tab.Screen name="Explore" component={ExploreScreen} />
        <Tab.Screen name="Profile" component={ProfileScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
};

export default App;
