import React, {useMemo, useState} from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {LegendList} from '@legendapp/list/react-native';
import type {LegendListRenderItemProps} from '@legendapp/list/react-native';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {useHeroes} from '../hooks/useHeroes';
import type {Hero} from '../../domain/entities/Hero';
import HeroCard from '../components/HeroCard';
import StateView from '../components/StateView';
import type {RootStackParamList} from '../navigation/types';
import colors from '../theme/colors';

type Navigation = NativeStackNavigationProp<RootStackParamList>;

const HORIZONTAL_PADDING = 16;
const COLUMN_GAP = 12;

const HomeScreen = () => {
  const {heroes, isLoading, error, refetch, isRefetching} = useHeroes();
  const navigation = useNavigation<Navigation>();
  const {width} = useWindowDimensions();
  const [query, setQuery] = useState('');

  const cardWidth = (width - HORIZONTAL_PADDING * 2 - COLUMN_GAP) / 2;

  const filteredHeroes = useMemo(() => {
    const term = query.trim().toLowerCase();
    const sorted = [...heroes].sort((a, b) => a.name.localeCompare(b.name));

    if (!term) {
      return sorted;
    }

    return sorted.filter(
      hero =>
        hero.name.toLowerCase().includes(term) ||
        hero.roles.some(role => role.toLowerCase().includes(term)) ||
        hero.primaryAttr.includes(term),
    );
  }, [heroes, query]);

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
        <Text style={styles.title}>Dota 2 Heroes</Text>
        <Text style={styles.subtitle}>
          {isLoading ? 'Loading roster...' : `${filteredHeroes.length} heroes`}
        </Text>

        <View style={styles.searchBox}>
          <Icon name="search" size={18} color={colors.textFaint} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search by name or role"
            placeholderTextColor={colors.textFaint}
            autoCorrect={false}
            autoCapitalize="none"
            returnKeyType="search"
            style={styles.searchInput}
          />
          {query ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              onPress={() => setQuery('')}
              hitSlop={8}>
              <Icon name="close-circle" size={18} color={colors.textFaint} />
            </Pressable>
          ) : null}
        </View>
      </View>

      {isLoading ? (
        <StateView loading title="Summoning the heroes" />
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
              title="No heroes found"
              message={`Nothing matches "${query.trim()}".`}
            />
          }
        />
      )}
    </SafeAreaView>
  );
};

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
    letterSpacing: 0.2,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    marginTop: 2,
  },
  searchBox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 12,
    borderWidth: 1,
    flexDirection: 'row',
    marginTop: 14,
    paddingHorizontal: 12,
  },
  searchInput: {
    color: colors.text,
    flex: 1,
    fontSize: 14,
    paddingVertical: 11,
    paddingHorizontal: 8,
  },
  column: {
    gap: COLUMN_GAP,
    paddingHorizontal: HORIZONTAL_PADDING,
  },
  listContent: {
    paddingBottom: 120,
    paddingTop: 14,
  },
});

export default HomeScreen;
