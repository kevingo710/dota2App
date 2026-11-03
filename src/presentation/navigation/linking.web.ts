import {
  getPathFromState as getPathFromStateDefault,
  getStateFromPath as getStateFromPathDefault,
} from '@react-navigation/native';
import type {LinkingOptions} from '@react-navigation/native';
import type {RootStackParamList} from './types';

// The React Native tsconfig has no DOM types; this file only runs in a browser.
declare const window: {location: {pathname: string}};

type ParsedState = NonNullable<ReturnType<typeof getStateFromPathDefault>>;

const HOME_ROUTE = '/';

// useLinking reuses route.path as the next URL, which would drop the base path.
const withoutPaths = (state: ParsedState): ParsedState => ({
  ...state,
  routes: state.routes.map(({path: _path, ...route}) =>
    route.state
      ? {...route, state: withoutPaths(route.state as ParsedState)}
      : route,
  ),
});

// Routes live in the query string: GitHub Pages has no fallback for nested
// paths, and relative data URLs (heroDataUrl.web.ts) need the base path intact.
// The base is read on every call so one bundle works at any path and in the
// landing page's iframe. Only the text after '?' is parsed; unknown routes
// open Home.
const getStateFromPath: typeof getStateFromPathDefault = (path, options) => {
  const route = path.split('?')[1] || HOME_ROUTE;
  const state =
    getStateFromPathDefault(route, options) ??
    getStateFromPathDefault(HOME_ROUTE, options);
  return state && withoutPaths(state);
};

// Must equal location.pathname + location.search: useLinking compares the two
// to decide whether a history entry can restore its saved state.
const getPathFromState: typeof getPathFromStateDefault = (state, options) => {
  const route = getPathFromStateDefault(state, options);
  const {pathname} = window.location;
  return route === HOME_ROUTE ? pathname : `${pathname}?${route}`;
};

export const linking: LinkingOptions<RootStackParamList> = {
  prefixes: [],
  config: {
    initialRouteName: 'Tabs',
    screens: {
      Tabs: {
        screens: {
          Home: '',
          Explore: 'explore',
          Superstar: 'superstar',
          Settings: 'settings',
        },
      },
      HeroDetail: {
        path: 'hero/:heroId(\\d+)',
        parse: {heroId: Number},
      },
    },
  },
  getStateFromPath,
  getPathFromState,
};
