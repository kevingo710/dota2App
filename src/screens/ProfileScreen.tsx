import {View, Text, Image} from 'react-native';
import React from 'react';
import colors from '../styles/colors';

const ProfileScreen = () => {
  return (
    <View style={{padding: 15}}>
      <Text>ProfileScreen</Text>
      <View
        style={{alignItems: 'center', justifyContent: 'center', padding: 15}}>
        <Image
          source={require('../../assets/jugger.png')}
          style={{width: 350, height: 350, marginTop: 20}}
          resizeMode={'contain'}
        />
      </View>

      <View style={{alignSelf: 'flex-start'}}>
        <View
          style={{
            backgroundColor: colors.orange,
            width: 'auto',
            height: 'auto',
            borderRadius: 50,
            padding: 6,
          }}>
          <Text style={{color: 'white'}}>Carry, Jungler</Text>
        </View>
      </View>

      <Text
        style={{
          color: 'white',
          fontSize: 35,
          fontWeight: 'bold',
          marginTop: 10,
        }}>
        Juggernaut
      </Text>
      <Text
        style={{
          color: colors.orange,
          fontSize: 15,
          fontWeight: 'bold',
          marginTop: 10,
        }}>
        Hero Skills
      </Text>
      <View
        style={{
          justifyContent: 'space-between',

          flexDirection: 'row',
        }}>
        <Image
          source={{
            uri: 'https://es.dotabuff.com/assets/skills/juggernaut-blade-fury-5028-c682d3dc9e7ee16d832b619965d4a9642e5b85f264d262192db403b6f590ba3f.jpg',
          }}
          style={{width: 60, height: 60, marginTop: 20, borderRadius: 50}}
          resizeMode={'contain'}
        />
        <Image
          source={{
            uri: 'https://es.dotabuff.com/assets/skills/juggernaut-healing-ward-5029-ed1059016706a0d6a58b43210dab4bbec09ed8d608cb3893e62236477a795e77.jpg',
          }}
          style={{width: 60, height: 60, marginTop: 20, borderRadius: 50}}
          resizeMode={'contain'}
        />
        <Image
          source={{
            uri: 'https://es.dotabuff.com/assets/skills/juggernaut-blade-dance-5027-46c750263ee89766d70d6fbdf14bd98379accb234bf6d79fdbdbbe93ca8ec555.jpg',
          }}
          style={{width: 60, height: 60, marginTop: 20, borderRadius: 50}}
          resizeMode={'contain'}
        />
        <Image
          source={{
            uri: 'https://es.dotabuff.com/assets/skills/juggernaut-omnislash-5030-685c0ee36de9525047aab7faced224dc94c5a0bf061bbb48264adec9b423e9b3.jpg',
          }}
          style={{width: 60, height: 60, marginTop: 20, borderRadius: 50}}
          resizeMode={'contain'}
        />
      </View>
    </View>
  );
};

export default ProfileScreen;
