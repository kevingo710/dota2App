import {View, Text} from 'react-native';
import React from 'react';
import Icon from 'react-native-vector-icons/Ionicons';

const HomeScreen = () => {
  return (
    <View>
      <Text>HomeScreen</Text>
      <Text>
        <Icon name="airplane-outline" size={80} color="#900" />
      </Text>
    </View>
  );
};

export default HomeScreen;
