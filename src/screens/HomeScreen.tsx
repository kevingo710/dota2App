import {View, Text, Image} from 'react-native';
import React, {useMemo} from 'react';
import {LegendList} from '@legendapp/list/react-native';
import type {LegendListRenderItemProps} from '@legendapp/list/react-native';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {useHeroStats} from '../hooks/useHeroStats';
import {SimpleHero} from '../interfaces/heroInterfaces';

const renderPicture = ({item}: LegendListRenderItemProps<SimpleHero>) => (
  <Image
    source={{uri: item.picture}}
    style={{width: 120, height: 120, borderRadius: 100}}
  />
);

const HomeScreen = () => {
  const {simpleHeroList} = useHeroStats();
  const heroesWithPicture = useMemo(
    () => simpleHeroList.filter(hero => hero.picture),
    [simpleHeroList],
  );

  return (
    <View style={{flex: 1}}>
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
    </View>
  );
};

export default HomeScreen;
