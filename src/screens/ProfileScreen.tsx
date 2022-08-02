import {View, Text, Image, ScrollView} from 'react-native';
import React from 'react';
import colors from '../styles/colors';

const ProfileScreen = () => {
  return (
    <ScrollView
      contentContainerStyle={{paddingBottom: 50}}
      style={{padding: 15, marginBottom: 80, flex: 1}}>
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
      <Text
        style={{
          color: colors.orange,
          fontSize: 15,
          fontWeight: 'bold',
          marginTop: 20,
        }}>
        Story Of Juggernaut
      </Text>
      <Text
        style={{
          color: 'white',
          fontSize: 15,
          textAlign: 'justify',
          marginTop: 10,
        }}>
        No one has ever seen the face hidden beneath the mask of Yurnero the
        Juggernaut. It is only speculation that he even has one. For defying a
        corrupt lord, Yurnero was exiled from the ancient Isle of Masks--a
        punishment that saved his life. The isle soon after vanished beneath the
        waves in a night of vengeful magic. He alone remains to carry on the
        Isle's long Juggernaut tradition, one of ritual and swordplay. The last
        practitioner of the art, Yurnero's confidence and courage are the result
        of endless practice; his inventive bladework proves that he has never
        stopped challenging himself. Still, his motives are as unreadable as his
        expression. For a hero who has lost everything twice over, he fights as
        if victory is a foregone conclusion.
      </Text>
    </ScrollView>
  );
};

export default ProfileScreen;
