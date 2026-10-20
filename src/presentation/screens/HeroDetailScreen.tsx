import React, {useMemo} from 'react';
import {
  ActivityIndicator,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import type {RootStackParamList} from '../navigation/types';
import {useHeroes} from '../hooks/useHeroes';
import {useHeroDetails} from '../hooks/useHeroDetails';
import AttributePill from '../components/AttributePill';
import StateView from '../components/StateView';
import type {HeroAbility} from '../../domain/entities/HeroDetails';
import {attributeMeta} from '../theme/heroMeta';
import colors from '../theme/colors';

type Props = NativeStackScreenProps<RootStackParamList, 'HeroDetail'>;

const COMPLEXITY_LABELS = ['Simple', 'Moderate', 'Complex'];

const StatTile = ({label, value}: {label: string; value: string}) => (
  <View style={styles.statTile}>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={styles.statValue}>{value}</Text>
  </View>
);

const AbilityRow = ({ability}: {ability: HeroAbility}) => (
  <View style={styles.abilityRow}>
    <Image source={{uri: ability.icon}} style={styles.abilityIcon} />
    <View style={styles.abilityBody}>
      <View style={styles.abilityHeader}>
        <Text style={styles.abilityName}>{ability.displayName}</Text>
        {ability.isUltimate ? (
          <View style={styles.ultimateBadge}>
            <Text style={styles.ultimateBadgeLabel}>ULTIMATE</Text>
          </View>
        ) : null}
      </View>
      <Text style={styles.abilityMeta}>
        Mana {ability.manaCost} · Cooldown {ability.cooldown}
      </Text>
      <Text style={styles.abilityDescription}>{ability.description}</Text>
      {ability.lore ? (
        <Text style={styles.abilityLore}>{ability.lore}</Text>
      ) : null}
    </View>
  </View>
);

const HeroDetailScreen = ({route, navigation}: Props) => {
  const {heroId} = route.params;
  const insets = useSafeAreaInsets();
  const {heroes} = useHeroes();
  const hero = useMemo(
    () => heroes.find(item => item.id === heroId),
    [heroes, heroId],
  );
  const {details, isLoading, error, refetch, isRefetching} =
    useHeroDetails(heroId);

  const picture = hero?.picture ?? details?.picture;
  const name = hero?.name ?? details?.name ?? 'Hero';
  const attribute = hero?.primaryAttr ?? 'all';
  const meta = attributeMeta(attribute);

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={{paddingBottom: insets.bottom + 32}}
        refreshControl={
          <RefreshControl
            tintColor={colors.orange}
            colors={[colors.orange]}
            refreshing={isRefetching}
            onRefresh={() => {
              refetch();
            }}
          />
        }>
        <View style={styles.heroBanner}>
          {picture ? (
            <Image source={{uri: picture}} style={styles.heroImage} />
          ) : (
            <View style={styles.heroImagePlaceholder}>
              <Text style={styles.heroImagePlaceholderText}>{name}</Text>
            </View>
          )}
          <View style={styles.bannerFade} />
        </View>

        <View style={styles.content}>
          <View style={styles.titleRow}>
            <Text style={styles.heroName}>{name}</Text>
            <View
              style={[
                styles.attributeBar,
                {backgroundColor: meta.color},
              ]}
            />
          </View>

          <View style={styles.badgeRow}>
            <AttributePill attribute={attribute} />
            {hero ? (
              <View style={styles.chip}>
                <Text style={styles.chipLabel}>{hero.attackType}</Text>
              </View>
            ) : null}
            {details ? (
              <View style={styles.chip}>
                <Text style={styles.chipLabel}>
                  {COMPLEXITY_LABELS[details.complexity - 1] ?? 'Moderate'}
                </Text>
              </View>
            ) : null}
          </View>

          {hero?.roles.length ? (
            <View style={styles.rolesRow}>
              {hero.roles.map(role => (
                <View key={role} style={styles.roleChip}>
                  <Text style={styles.roleLabel}>{role}</Text>
                </View>
              ))}
            </View>
          ) : null}

          {details?.hype ? (
            <Text style={styles.hype}>{details.hype}</Text>
          ) : null}

          {isLoading ? (
            <ActivityIndicator
              color={colors.orange}
              size="large"
              style={styles.loader}
            />
          ) : null}

          {error && !isLoading ? (
            <StateView
              title="Could not load hero details"
              message="Check your connection and try again."
              actionLabel="Retry"
              onAction={refetch}
            />
          ) : null}

          {details ? (
            <>
              <Text style={styles.sectionTitle}>Attributes</Text>
              <View style={styles.statsGrid}>
                <StatTile
                  label="Strength"
                  value={`${details.stats.strength} +${details.stats.strengthGain}`}
                />
                <StatTile
                  label="Agility"
                  value={`${details.stats.agility} +${details.stats.agilityGain}`}
                />
                <StatTile
                  label="Intelligence"
                  value={`${details.stats.intelligence} +${details.stats.intelligenceGain}`}
                />
                <StatTile label="Damage" value={details.stats.damage} />
                <StatTile label="Armor" value={details.stats.armor} />
                <StatTile
                  label="Move speed"
                  value={`${details.stats.movementSpeed}`}
                />
                <StatTile
                  label="Attack range"
                  value={`${details.stats.attackRange}`}
                />
                <StatTile
                  label="Attack speed"
                  value={`${details.stats.attackRate}`}
                />
                <StatTile
                  label="Magic resist"
                  value={`${details.stats.magicResistance}%`}
                />
                <StatTile
                  label="Health"
                  value={`${details.stats.maxHealth} +${details.stats.healthRegen}`}
                />
                <StatTile
                  label="Mana"
                  value={`${details.stats.maxMana} +${details.stats.manaRegen}`}
                />
                <StatTile
                  label="Vision"
                  value={`${details.stats.sightRangeDay} / ${details.stats.sightRangeNight}`}
                />
              </View>

              <Text style={styles.sectionTitle}>Abilities</Text>
              {details.abilities.map(ability => (
                <AbilityRow key={ability.id} ability={ability} />
              ))}

              <Text style={styles.sectionTitle}>Lore</Text>
              <Text style={styles.lore}>{details.lore}</Text>
            </>
          ) : null}
        </View>
      </ScrollView>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Go back"
        onPress={navigation.goBack}
        style={({pressed}) => [
          styles.backButton,
          {top: insets.top + 8},
          pressed && styles.pressed,
        ]}>
        <Icon name="chevron-back" size={24} color={colors.text} />
      </Pressable>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.darkBlue,
    flex: 1,
  },
  heroBanner: {
    backgroundColor: colors.darkBlueLight,
    width: '100%',
  },
  heroImage: {
    aspectRatio: 16 / 9,
    width: '100%',
  },
  heroImagePlaceholder: {
    alignItems: 'center',
    aspectRatio: 16 / 9,
    justifyContent: 'center',
    width: '100%',
  },
  heroImagePlaceholderText: {
    color: colors.textMuted,
    fontSize: 18,
  },
  bannerFade: {
    backgroundColor: colors.darkBlue,
    bottom: 0,
    height: 24,
    left: 0,
    position: 'absolute',
    right: 0,
  },
  content: {
    paddingHorizontal: 18,
    paddingTop: 12,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
  },
  heroName: {
    color: colors.text,
    fontSize: 30,
    fontWeight: '800',
    letterSpacing: 0.2,
  },
  attributeBar: {
    borderRadius: 3,
    height: 22,
    marginLeft: 10,
    width: 4,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 10,
  },
  chip: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 999,
    borderWidth: 1,
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
    marginTop: 10,
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
    letterSpacing: 0.3,
  },
  hype: {
    color: colors.textMuted,
    fontSize: 14,
    fontStyle: 'italic',
    lineHeight: 21,
    marginTop: 16,
  },
  loader: {
    marginVertical: 32,
  },
  sectionTitle: {
    color: colors.orange,
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 0.4,
    marginBottom: 12,
    marginTop: 26,
    textTransform: 'uppercase',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  statTile: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
    width: '31.5%',
  },
  statLabel: {
    color: colors.textFaint,
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  statValue: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '700',
    marginTop: 3,
  },
  abilityRow: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    flexDirection: 'row',
    marginBottom: 12,
    padding: 12,
  },
  abilityIcon: {
    backgroundColor: colors.darkBlueLight,
    borderRadius: 10,
    height: 56,
    width: 56,
  },
  abilityBody: {
    flex: 1,
    marginLeft: 12,
  },
  abilityHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  abilityName: {
    color: colors.text,
    fontSize: 15,
    fontWeight: '700',
  },
  ultimateBadge: {
    backgroundColor: colors.orange,
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  ultimateBadgeLabel: {
    color: colors.darkBlue,
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.4,
  },
  abilityMeta: {
    color: colors.textFaint,
    fontSize: 11,
    marginTop: 3,
  },
  abilityDescription: {
    color: colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 6,
  },
  abilityLore: {
    color: colors.textFaint,
    fontSize: 11,
    fontStyle: 'italic',
    lineHeight: 16,
    marginTop: 6,
  },
  lore: {
    color: colors.textMuted,
    fontSize: 14,
    lineHeight: 22,
  },
  backButton: {
    alignItems: 'center',
    backgroundColor: 'rgba(20, 14, 54, 0.75)',
    borderColor: colors.border,
    borderRadius: 20,
    borderWidth: 1,
    height: 40,
    justifyContent: 'center',
    left: 14,
    position: 'absolute',
    width: 40,
  },
  pressed: {
    opacity: 0.7,
  },
});

export default HeroDetailScreen;
