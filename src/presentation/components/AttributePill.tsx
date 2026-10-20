import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {HeroAttribute} from '../../domain/entities/Hero';
import {attributeMeta} from '../theme/heroMeta';
import colors from '../theme/colors';

interface AttributePillProps {
  attribute: HeroAttribute;
  compact?: boolean;
}

const AttributePill = ({attribute, compact = false}: AttributePillProps) => {
  const meta = attributeMeta(attribute);

  return (
    <View
      style={[
        styles.pill,
        compact && styles.compactPill,
        {borderColor: meta.color},
      ]}>
      <View style={[styles.dot, {backgroundColor: meta.color}]} />
      <Text style={[styles.label, compact && styles.compactLabel]}>
        {compact ? meta.shortLabel : meta.label}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    alignItems: 'center',
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  compactPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  dot: {
    borderRadius: 3,
    height: 6,
    marginRight: 6,
    width: 6,
  },
  label: {
    color: colors.text,
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  compactLabel: {
    fontSize: 10,
  },
});

export default AttributePill;
