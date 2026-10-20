import React, {useMemo, useState} from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {LegendList} from '@legendapp/list/react-native';
import type {LegendListRenderItemProps} from '@legendapp/list/react-native';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {useHeroes} from '../hooks/useHeroes';
import type {Hero, HeroAttribute} from '../../domain/entities/Hero';
import HeroCard from '../components/HeroCard';
import StateView from '../components/StateView';
import {heroAttributes, heroRoles} from '../theme/heroMeta';
import type {RootStackParamList} from '../navigation/types';
import colors from '../theme/colors';

type Navigation = NativeStackNavigationProp<RootStackParamList>;
type AttributeFilter = HeroAttribute | 'any';

const HORIZONTAL_PADDING = 16;
const COLUMN_GAP = 12;

const ExploreScreen = () => {
  const {heroes, isLoading, error, refetch, isRefetching} = useHeroes();
  const navigation = useNavigation<Navigation>();
  const {width} = useWindowDimensions();
  const [attribute, setAttribute] = useState<AttributeFilter>('any');
  const [role, setRole] = useState<string | null>(null);

  const cardWidth = (width - HORIZONTAL_PADDING * 2 - COLUMN_GAP) / 2;

  const filteredHeroes = useMemo(
    () =>
      heroes.filter(hero => {
        const matchesAttribute =
          attribute === 'any' || hero.primaryAttr === attribute;
        const matchesRole = !role || hero.roles.includes(role);
        return matchesAttribute && matchesRole;
      }),
    [attribute, role, heroes],
  );

  const hasFilters = attribute !== 'any' || role !== null;

  const renderHero = ({item}: LegendListRenderItemProps<Hero>) => (
    <View style={{width: cardWidth}}>
      <HeroCard
        hero={item}
        onPress={() => navigation.navigate('HeroDetail', {heroId: item.id})}
      />
    </View>
  );

  return (
    <SafeAreaView edges={['top']} style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Explore</Text>
        <Text style={styles.subtitle}>
          Filter the roster by attribute and role.
        </Text>
      </View>

      <View style={styles.chipRow}>
        <FilterChip
          label="Any"
          active={attribute === 'any'}
          onPress={() => setAttribute('any')}
        />
        {heroAttributes.map(meta => (
          <FilterChip
            key={meta.value}
            label={meta.label}
            color={meta.color}
            active={attribute === meta.value}
            onPress={() => setAttribute(meta.value)}
          />
        ))}
      </View>

      <View style={styles.chipRow}>
        <FilterChip
          label="All roles"
          active={role === null}
          onPress={() => setRole(null)}
        />
        {heroRoles.map(item => (
          <FilterChip
            key={item}
            label={item}
            active={role === item}
            onPress={() => setRole(role === item ? null : item)}
          />
        ))}
      </View>

      <View style={styles.resultsRow}>
        <Text style={styles.results}>
          {isLoading ? 'Loading...' : `${filteredHeroes.length} heroes`}
        </Text>
        {hasFilters ? (
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              setAttribute('any');
              setRole(null);
            }}>
            <Text style={styles.reset}>Reset filters</Text>
          </Pressable>
        ) : null}
      </View>

      {isLoading ? (
        <StateView loading title="Loading heroes" />
      ) : error ? (
        <StateView
          title="Could not load heroes"
          message="Check your connection and try again."
          actionLabel="Retry"
          onAction={refetch}
        />
      ) : (
        <LegendList
          data={filteredHeroes}
          renderItem={renderHero}
          keyExtractor={hero => `${hero.id}`}
          numColumns={2}
          recycleItems
          estimatedItemSize={190}
          columnWrapperStyle={styles.column}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          refreshing={isRefetching}
          onRefresh={refetch}
          ListEmptyComponent={
            <StateView
              title="No heroes match"
              message="Try a different attribute or role combination."
            />
          }
        />
      )}
    </SafeAreaView>
  );
};

const FilterChip = ({
  label,
  active,
  color,
  onPress,
}: {
  label: string;
  active: boolean;
  color?: string;
  onPress: () => void;
}) => (
  <Pressable
    accessibilityRole="button"
    accessibilityState={{selected: active}}
    onPress={onPress}
    style={({pressed}) => [
      styles.chip,
      active && styles.activeChip,
      pressed && styles.pressed,
    ]}>
    {color ? (
      <View style={[styles.chipDot, {backgroundColor: color}]} />
    ) : null}
    <Text style={[styles.chipLabel, active && styles.activeChipLabel]}>
      {label}
    </Text>
  </Pressable>
);

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.darkBlue,
    flex: 1,
  },
  header: {
    paddingHorizontal: HORIZONTAL_PADDING,
    paddingTop: 12,
  },
  title: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '800',
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    marginTop: 2,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    paddingHorizontal: HORIZONTAL_PADDING,
    paddingTop: 12,
  },
  chip: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  activeChip: {
    backgroundColor: colors.orange,
    borderColor: colors.orange,
  },
  pressed: {
    opacity: 0.7,
  },
  chipDot: {
    borderRadius: 4,
    height: 8,
    marginRight: 6,
    width: 8,
  },
  chipLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '600',
  },
  activeChipLabel: {
    color: colors.darkBlue,
  },
  resultsRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: HORIZONTAL_PADDING,
    paddingTop: 14,
  },
  results: {
    color: colors.textMuted,
    fontSize: 12,
  },
  reset: {
    color: colors.orange,
    fontSize: 12,
    fontWeight: '700',
  },
  column: {
    gap: COLUMN_GAP,
    paddingHorizontal: HORIZONTAL_PADDING,
  },
  listContent: {
    paddingBottom: 120,
    paddingTop: 10,
  },
});

export default ExploreScreen;
