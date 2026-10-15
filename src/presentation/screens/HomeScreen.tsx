import {Text, Image} from 'react-native';
import React, {useMemo} from 'react';
import {SafeAreaView} from 'react-native-safe-area-context';
import {LegendList} from '@legendapp/list/react-native';
import type {LegendListRenderItemProps} from '@legendapp/list/react-native';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {useHeroes} from '../hooks/useHeroes';
import type {Hero} from '../../domain/entities/Hero';

const renderPicture = ({item}: LegendListRenderItemProps<Hero>) => (
  <Image
    source={{uri: item.picture}}
    style={{width: 120, height: 120, borderRadius: 100}}
  />
);

const HomeScreen = () => {
  const {heroes} = useHeroes();
  const heroesWithPicture = useMemo(
    () => heroes.filter(hero => hero.picture),
    [heroes],
  );

  return (
    <SafeAreaView edges={['top']} style={{flex: 1}}>
      <Text>HomeScreen</Text>
      <LegendList
        style={{flex: 1}}
        data={heroesWithPicture}
        renderItem={renderPicture}
        keyExtractor={hero => `${hero.id}`}
        estimatedItemSize={120}
        recycleItems
      />
      <Text>
        <Icon name="airplane-outline" size={80} color="#900" />
      </Text>
    </SafeAreaView>
  );
};

export default HomeScreen;
