import {View, Text, FlatList, Image, ActivityIndicator} from 'react-native';
import React from 'react';
import Icon from 'react-native-vector-icons/Ionicons';
import {useHeroStats} from '../hooks/useHeroStats';
import {SimpleHero} from '../interfaces/heroInterfaces';

const HomeScreen = () => {
  const {simpleHeroList, loadHeroes} = useHeroStats();
  console.log({simpleHeroList});

  const renderPicture = (item: SimpleHero) => {
    return (
      <Image
        source={{uri: item.picture}}
        style={{width: 120, height: 120, borderRadius: 100}}
      />
    );
  };

  const renderActivityIndicator = (item: SimpleHero) => {
    return (
      <ActivityIndicator
        size={50}
        style={{height: 20, width: 20}}
        color="grey"
        key={String(item.id)}
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
