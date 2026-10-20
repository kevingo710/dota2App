import React from 'react';
import {Image, Pressable, StyleSheet, Text, View} from 'react-native';
import type {Hero} from '../../domain/entities/Hero';
import AttributePill from './AttributePill';
import colors from '../theme/colors';

interface HeroCardProps {
  hero: Hero;
  onPress: () => void;
}

const HeroCard = ({hero, onPress}: HeroCardProps) => (
  <Pressable
    accessibilityRole="button"
    accessibilityLabel={`${hero.name}, ${hero.roles.join(', ')}`}
    onPress={onPress}
    style={({pressed}) => [styles.card, pressed && styles.pressed]}>
    <Image source={{uri: hero.picture}} style={styles.image} />
    <View style={styles.body}>
      <Text numberOfLines={1} style={styles.name}>
        {hero.name}
      </Text>
      <View style={styles.meta}>
        <AttributePill attribute={hero.primaryAttr} compact />
        <Text numberOfLines={1} style={styles.roles}>
          {hero.roles.slice(0, 2).join(' · ')}
        </Text>
      </View>
    </View>
  </Pressable>
);

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    flex: 1,
    marginBottom: 12,
    overflow: 'hidden',
  },
  pressed: {
    opacity: 0.7,
  },
  image: {
    aspectRatio: 16 / 9,
    backgroundColor: colors.darkBlueLight,
    width: '100%',
  },
  body: {
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  name: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
  },
  meta: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 6,
  },
  roles: {
    color: colors.textMuted,
    flex: 1,
    fontSize: 10,
    marginLeft: 6,
    textAlign: 'right',
  },
});

export default HeroCard;
