import {View, Text, FlatList, Image} from 'react-native';
import React from 'react';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {useHeroStats} from '../hooks/useHeroStats';
import {SimpleHero} from '../interfaces/heroInterfaces';

const HomeScreen = () => {
  const {simpleHeroList} = useHeroStats();
  console.log({simpleHeroList});

  const renderPicture = (item: SimpleHero) => {
    return (
      <Image
        source={{uri: item.picture}}
        style={{width: 120, height: 120, borderRadius: 100}}
      />
    );
  };

  return (
    <View>
      <Text>HomeScreen</Text>
      <FlatList
        data={simpleHeroList}
        keyExtractor={(hero, _index) => `${hero.id}`}
        renderItem={
          ({item}) => (item.picture ? renderPicture(item) : <></>)

          // <Text style={{color: 'white'}}>{item.id}</Text>
        }
        // onEndReached={loadHeroes}
        // onEndReachedThreshold={0.4}
      />
      <Text>
        <Icon name="airplane-outline" size={80} color="#900" />
      </Text>
    </View>
  );
};

export default HomeScreen;
