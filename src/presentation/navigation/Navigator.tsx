import {Platform} from 'react-native';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import React from 'react';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import HomeScreen from '../screens/HomeScreen';
import SettingsScreen from '../screens/SettingsScreen';
import ExploreScreen from '../screens/ExploreScreen';
import SuperstarScreen from '../screens/SuperstarScreen';
import HeroDetailScreen from '../screens/HeroDetailScreen';
import type {RootStackParamList, TabParamList} from './types';
import colors from '../theme/colors';

const Tab = createBottomTabNavigator<TabParamList>();
// Web clips tab labels to one line, and beside the icon a 390px bar leaves
// "Superstar" ~49px; iOS lets the text overflow its box, so it keeps the row.
const LABEL_POSITION = Platform.OS === 'web' ? 'below-icon' : 'beside-icon';
const Stack = createNativeStackNavigator<RootStackParamList>();

interface TabIconProps {
  color: string;
  size: number;
}

const HomeIcon = ({color, size}: TabIconProps) => (
  <Icon name="home-outline" color={color} size={size} />
);

const ExploreIcon = ({color, size}: TabIconProps) => (
  <Icon name="compass-outline" color={color} size={size} />
);

const SuperstarIcon = ({color, size}: TabIconProps) => (
  <Icon name="star-outline" color={color} size={size} />
);

const SettingsIcon = ({color, size}: TabIconProps) => (
  <Icon name="settings-outline" color={color} size={size} />
);

const Tabs = () => {
  return (
    <Tab.Navigator
      initialRouteName="Home"
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.orange,
        tabBarInactiveTintColor: colors.textFaint,
        tabBarHideOnKeyboard: true,
        tabBarStyle: {
          paddingVertical: Platform.OS === 'ios' ? 20 : 0,
          height: 90,
          paddingHorizontal: 5,
          paddingTop: 0,
          backgroundColor: colors.darkBlue,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          position: 'absolute',
        },
      }}>
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarLabel: 'Home',
          tabBarIcon: HomeIcon,
          tabBarLabelPosition: LABEL_POSITION,
        }}
      />
      <Tab.Screen
        name="Explore"
        component={ExploreScreen}
        options={{
          tabBarLabel: 'Explore',
          tabBarIcon: ExploreIcon,
          tabBarLabelPosition: LABEL_POSITION,
        }}
      />
      <Tab.Screen
        name="Superstar"
        component={SuperstarScreen}
        options={{
          tabBarLabel: 'Superstar',
          tabBarIcon: SuperstarIcon,
          tabBarLabelPosition: LABEL_POSITION,
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          tabBarLabel: 'Settings',
          tabBarIcon: SettingsIcon,
          tabBarLabelPosition: LABEL_POSITION,
        }}
      />
    </Tab.Navigator>
  );
};

const Navigator = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: {backgroundColor: colors.darkBlue},
      }}>
      <Stack.Screen name="Tabs" component={Tabs} />
      <Stack.Screen name="HeroDetail" component={HeroDetailScreen} />
    </Stack.Navigator>
  );
};

export default Navigator;
