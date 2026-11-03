import {linking} from '../../src/presentation/navigation/linking.web';

// useLinking always passes the config as the second argument.
const getStateFromPath = (path: string) =>
  linking.getStateFromPath!(path, linking.config as any);
const getPathFromState = (state: any) =>
  linking.getPathFromState!(state, linking.config as any);

const setPathname = (pathname: string) => {
  Object.defineProperty(globalThis, 'window', {
    value: {location: {pathname}},
    configurable: true,
    writable: true,
  });
};

const originalWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');

afterAll(() => {
  if (originalWindow) {
    Object.defineProperty(globalThis, 'window', originalWindow);
  } else {
    delete (globalThis as any).window;
  }
});

const names = (state: any) => state.routes.map((r: any) => r.name);
const tabState = (name: string) => ({
  routes: [{name: 'Tabs', state: {routes: [{name}], index: 0}}],
  index: 0,
});
const heroState = (heroId: number) => ({
  routes: [{name: 'Tabs'}, {name: 'HeroDetail', params: {heroId}}],
  index: 1,
});
const focusedTab = (state: any) => {
  const tabs = state.routes[0].state;
  return tabs.routes[tabs.index ?? 0].name;
};

describe.each(['/', '/mobadex/app/'])('linking.web at base %s', base => {
  beforeEach(() => setPathname(base));

  it('writes Home as the bare base path', () => {
    expect(getPathFromState(tabState('Home') as any)).toBe(base);
  });

  it.each([
    ['Explore', 'explore'],
    ['Superstar', 'superstar'],
    ['Settings', 'settings'],
  ])('writes %s as a query route under the base', (screen, route) => {
    expect(getPathFromState(tabState(screen) as any)).toBe(
      `${base}?/${route}`,
    );
  });

  it('writes a hero detail as ?/hero/<id>', () => {
    expect(getPathFromState(heroState(8) as any)).toBe(`${base}?/hero/8`);
  });

  it('never writes a hash fragment', () => {
    const outputs = [
      tabState('Home'),
      tabState('Explore'),
      tabState('Superstar'),
      tabState('Settings'),
      heroState(8),
    ].map(s => getPathFromState(s as any));
    outputs.forEach(o => expect(o).not.toContain('#'));
  });

  it.each(['Home', 'Explore', 'Superstar', 'Settings'])(
    'round trips the %s tab',
    screen => {
      const path = getPathFromState(tabState(screen) as any);
      const parsed = getStateFromPath(path)!;
      expect(names(parsed)).toEqual(['Tabs']);
      expect(focusedTab(parsed)).toBe(screen);
      expect(getPathFromState(parsed as any)).toBe(path);
    },
  );

  it('round trips HeroDetail with a numeric heroId', () => {
    const path = getPathFromState(heroState(8) as any);
    const parsed: any = getStateFromPath(path);
    expect(names(parsed)).toEqual(['Tabs', 'HeroDetail']);
    expect(parsed.index).toBe(1);
    expect(parsed.routes[1].params).toEqual({heroId: 8});
    expect(typeof parsed.routes[1].params.heroId).toBe('number');
    expect(getPathFromState(parsed)).toBe(path);
  });

  it('opens Home for the bare base path', () => {
    const parsed = getStateFromPath(base)!;
    expect(names(parsed)).toEqual(['Tabs']);
    expect(focusedTab(parsed)).toBe('Home');
  });

  it('leaves no path on any route so the base path cannot be dropped', () => {
    const json = JSON.stringify([
      getStateFromPath(`${base}?/hero/8`),
      getStateFromPath(`${base}?/explore`),
      getStateFromPath(base),
    ]);
    expect(json).not.toContain('"path"');
  });

  it.each(['?/hero/abc', '?/nope', '?utm=x'])(
    'does not open HeroDetail for %s',
    query => {
      const parsed = getStateFromPath(`${base}${query}`)!;
      expect(names(parsed)).not.toContain('HeroDetail');
      expect(focusedTab(parsed)).toBe('Home');
    },
  );
});

describe('linking.web config', () => {
  it('has no URL prefixes', () => {
    expect(linking.prefixes).toEqual([]);
  });

  it('ignores a pathname that merely looks like a route', () => {
    setPathname('/mobadex/app/');
    const parsed = getStateFromPath('/mobadex/app/explore')!;
    expect(focusedTab(parsed)).toBe('Home');
  });
});
