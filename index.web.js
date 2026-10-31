/**
 * @format
 */

import 'reflect-metadata';
import {AppRegistry} from 'react-native';
import App from './App';
import appJson from './app.json';

const appName = appJson.name;
// Importing the font makes webpack emit it; the URL is injected as @font-face below.
import ioniconsFontUrl from '@react-native-vector-icons/ionicons/fonts/Ionicons.ttf';

const fontStyle = document.createElement('style');
fontStyle.textContent = `@font-face { font-family: 'Ionicons'; src: url(${ioniconsFontUrl}) format('truetype'); }`;
document.head.appendChild(fontStyle);

AppRegistry.registerComponent(appName, () => App);
AppRegistry.runApplication(appName, {rootTag: document.getElementById('root')});
