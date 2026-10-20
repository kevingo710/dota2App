import type {HeroAttribute} from '../../domain/entities/Hero';

interface AttributeMeta {
  value: HeroAttribute;
  label: string;
  shortLabel: string;
  color: string;
}

export const heroAttributes: AttributeMeta[] = [
  {value: 'str', label: 'Strength', shortLabel: 'STR', color: '#E1543A'},
  {value: 'agi', label: 'Agility', shortLabel: 'AGI', color: '#3FBF6E'},
  {value: 'int', label: 'Intelligence', shortLabel: 'INT', color: '#39A7E0'},
  {value: 'all', label: 'Universal', shortLabel: 'UNI', color: '#C7A252'},
];

export const attributeMeta = (attribute: HeroAttribute): AttributeMeta =>
  heroAttributes.find(meta => meta.value === attribute) ?? heroAttributes[3];

export const heroRoles = [
  'Carry',
  'Support',
  'Nuker',
  'Disabler',
  'Initiator',
  'Escape',
  'Durable',
  'Pusher',
  'Jungler',
];
