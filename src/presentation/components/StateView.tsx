import React from 'react';
import {ActivityIndicator, Pressable, StyleSheet, Text, View} from 'react-native';
import colors from '../theme/colors';

interface StateViewProps {
  loading?: boolean;
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const StateView = ({
  loading = false,
  title,
  message,
  actionLabel,
  onAction,
}: StateViewProps) => (
  <View style={styles.container}>
    {loading ? (
      <ActivityIndicator color={colors.orange} size="large" />
    ) : null}
    <Text style={styles.title}>{title}</Text>
    {message ? <Text style={styles.message}>{message}</Text> : null}
    {actionLabel && onAction ? (
      <Pressable
        accessibilityRole="button"
        onPress={onAction}
        style={({pressed}) => [styles.button, pressed && styles.pressed]}>
        <Text style={styles.buttonLabel}>{actionLabel}</Text>
      </Pressable>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: 32,
  },
  title: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
    marginTop: 14,
    textAlign: 'center',
  },
  message: {
    color: colors.textMuted,
    fontSize: 13,
    marginTop: 6,
    textAlign: 'center',
  },
  button: {
    backgroundColor: colors.orange,
    borderRadius: 999,
    marginTop: 18,
    paddingHorizontal: 22,
    paddingVertical: 10,
  },
  pressed: {
    opacity: 0.75,
  },
  buttonLabel: {
    color: colors.darkBlue,
    fontSize: 13,
    fontWeight: '700',
  },
});

export default StateView;
