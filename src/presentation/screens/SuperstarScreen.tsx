import React, {useMemo} from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {useHeroes} from '../hooks/useHeroes';
import {useHeroDetails} from '../hooks/useHeroDetails';
import AttributePill from '../components/AttributePill';
import StateView from '../components/StateView';
import type {RootStackParamList} from '../navigation/types';
import colors from '../theme/colors';

type Navigation = NativeStackNavigationProp<RootStackParamList>;

const DAY_MS = 24 * 60 * 60 * 1000;

const SuperstarScreen = () => {
  const navigation = useNavigation<Navigation>();
  const {heroes, isLoading, error, refetch} = useHeroes();

  const hero = useMemo(() => {
    if (!heroes.length) {
      return undefined;
    }
    const dayIndex = Math.floor(Date.now() / DAY_MS) % heroes.length;
    return heroes[dayIndex];
  }, [heroes]);

  const {details, isLoading: isLoadingDetails} = useHeroDetails(hero?.id ?? 0);

  if (isLoading) {
    return (
      <SafeAreaView edges={['top']} style={styles.container}>
        <StateView loading title="Picking today's hero" />
      </SafeAreaView>
    );
  }

  if (error || !hero) {
    return (
      <SafeAreaView edges={['top']} style={styles.container}>
        <StateView
          title="Could not load the superstar"
          message="Check your connection and try again."
          actionLabel="Retry"
          onAction={refetch}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}>
        <Text style={styles.eyebrow}>HERO OF THE DAY</Text>
        <Text style={styles.title}>Superstar</Text>
        <Text style={styles.subtitle}>
          A new hero takes the stage every day.
        </Text>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`View ${hero.name} details`}
          onPress={() => navigation.navigate('HeroDetail', {heroId: hero.id})}
          style={({pressed}) => [styles.card, pressed && styles.pressed]}>
          <Image source={{uri: hero.picture}} style={styles.image} />
          <View style={styles.cardBody}>
            <Text style={styles.heroName}>{hero.name}</Text>
            <View style={styles.badgeRow}>
              <AttributePill attribute={hero.primaryAttr} />
              <View style={styles.chip}>
                <Text style={styles.chipLabel}>{hero.attackType}</Text>
              </View>
            </View>
            <View style={styles.rolesRow}>
              {hero.roles.map(role => (
                <View key={role} style={styles.roleChip}>
                  <Text style={styles.roleLabel}>{role}</Text>
                </View>
              ))}
            </View>
          </View>
        </Pressable>

        {isLoadingDetails ? (
          <ActivityIndicator
            color={colors.orange}
            style={styles.loader}
            size="large"
          />
        ) : details ? (
          <>
            <Text style={styles.quote}>“{details.hype}”</Text>

            <Text style={styles.sectionTitle}>At a glance</Text>
            <View style={styles.statsRow}>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{details.stats.damage}</Text>
                <Text style={styles.statLabel}>Damage</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{details.stats.armor}</Text>
                <Text style={styles.statLabel}>Armor</Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>
                  {details.stats.movementSpeed}
                </Text>
                <Text style={styles.statLabel}>Move speed</Text>
              </View>
            </View>

            <Text style={styles.sectionTitle}>Lore</Text>
            <Text numberOfLines={5} style={styles.lore}>
              {details.lore}
            </Text>
          </>
        ) : null}

        <Pressable
          accessibilityRole="button"
          onPress={() => navigation.navigate('HeroDetail', {heroId: hero.id})}
          style={({pressed}) => [styles.button, pressed && styles.pressed]}>
          <Text style={styles.buttonLabel}>View full details</Text>
          <Icon name="arrow-forward" size={16} color={colors.darkBlue} />
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.darkBlue,
    flex: 1,
  },
  content: {
    paddingBottom: 130,
    paddingHorizontal: 18,
    paddingTop: 12,
  },
  eyebrow: {
    color: colors.orange,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.6,
  },
  title: {
    color: colors.text,
    fontSize: 28,
    fontWeight: '800',
    marginTop: 2,
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 13,
    marginTop: 2,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 18,
    borderWidth: 1,
    marginTop: 18,
    overflow: 'hidden',
  },
  pressed: {
    opacity: 0.75,
  },
  image: {
    aspectRatio: 16 / 9,
    backgroundColor: colors.darkBlueLight,
    width: '100%',
  },
  cardBody: {
    padding: 16,
  },
  heroName: {
    color: colors.text,
    fontSize: 24,
    fontWeight: '800',
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 10,
  },
  chip: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '600',
  },
  rolesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 12,
  },
  roleChip: {
    backgroundColor: colors.surfaceLight,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  roleLabel: {
    color: colors.orange,
    fontSize: 11,
    fontWeight: '700',
  },
  loader: {
    marginVertical: 32,
  },
  quote: {
    color: colors.textMuted,
    fontSize: 14,
    fontStyle: 'italic',
    lineHeight: 21,
    marginTop: 20,
  },
  sectionTitle: {
    color: colors.orange,
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0.6,
    marginBottom: 10,
    marginTop: 22,
    textTransform: 'uppercase',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 10,
  },
  statCard: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 12,
    borderWidth: 1,
    flex: 1,
    paddingVertical: 12,
  },
  statValue: {
    color: colors.text,
    fontSize: 17,
    fontWeight: '800',
  },
  statLabel: {
    color: colors.textFaint,
    fontSize: 10,
    marginTop: 3,
    textTransform: 'uppercase',
  },
  lore: {
    color: colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  button: {
    alignItems: 'center',
    backgroundColor: colors.orange,
    borderRadius: 999,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginTop: 24,
    paddingVertical: 14,
  },
  buttonLabel: {
    color: colors.darkBlue,
    fontSize: 14,
    fontWeight: '800',
  },
});

export default SuperstarScreen;
