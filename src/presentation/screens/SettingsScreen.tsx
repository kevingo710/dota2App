import React from 'react';
import {
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {useQueryClient} from '@tanstack/react-query';
import {Ionicons as Icon} from '@react-native-vector-icons/ionicons/static';
import {version} from '../../../package.json';
import colors from '../theme/colors';

const Row = ({
  label,
  value,
  onPress,
  destructive,
}: {
  label: string;
  value?: string;
  onPress?: () => void;
  destructive?: boolean;
}) => {
  const content = (
    <>
      <Text style={[styles.rowLabel, destructive && styles.destructive]}>
        {label}
      </Text>
      <View style={styles.rowValueWrap}>
        {value ? <Text style={styles.rowValue}>{value}</Text> : null}
        {onPress ? (
          <Icon name="chevron-forward" size={16} color={colors.textFaint} />
        ) : null}
      </View>
    </>
  );

  if (!onPress) {
    return <View style={styles.row}>{content}</View>;
  }

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({pressed}) => [styles.row, pressed && styles.pressed]}>
      {content}
    </Pressable>
  );
};

const SettingsScreen = () => {
  const queryClient = useQueryClient();

  const clearCache = () => {
    Alert.alert(
      'Clear cached data',
      'Heroes and details will be downloaded again on next use.',
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => {
            queryClient.clear();
            Alert.alert('Cache cleared', 'Fresh data will load from the API.');
          },
        },
      ],
    );
  };

  const refreshData = () => {
    queryClient.invalidateQueries({queryKey: ['heroes']});
  };

  return (
    <SafeAreaView edges={['top']} style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}>
        <Text style={styles.title}>Settings</Text>
        <Text style={styles.subtitle}>App information and cached data.</Text>

        <Text style={styles.sectionTitle}>Data</Text>
        <View style={styles.section}>
          <Row label="Hero roster" value="OpenDota" />
          <View style={styles.divider} />
          <Row label="Hero details" value="Valve Dota 2" />
          <View style={styles.divider} />
          <Row label="Refresh hero data" onPress={refreshData} />
        </View>

        <Text style={styles.sectionTitle}>Storage</Text>
        <View style={styles.section}>
          <Row label="Clear cached data" onPress={clearCache} destructive />
        </View>

        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.section}>
          <Row label="Version" value={version} />
          <View style={styles.divider} />
          <Row label="Platform" value={Platform.OS} />
        </View>

        <Text style={styles.footnote}>
          Dota 2 and all hero assets are property of Valve Corporation. This app
          uses community and official public data feeds for informational
          purposes.
        </Text>
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
  sectionTitle: {
    color: colors.orange,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
    marginBottom: 8,
    marginTop: 24,
    textTransform: 'uppercase',
  },
  section: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 14,
  },
  pressed: {
    opacity: 0.7,
  },
  rowLabel: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  destructive: {
    color: colors.danger,
  },
  rowValueWrap: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 6,
  },
  rowValue: {
    color: colors.textMuted,
    fontSize: 13,
  },
  divider: {
    backgroundColor: colors.border,
    height: 1,
    marginLeft: 14,
  },
  footnote: {
    color: colors.textFaint,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 24,
  },
});

export default SettingsScreen;
