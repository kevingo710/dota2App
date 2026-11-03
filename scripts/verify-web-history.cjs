// Browser scenarios for the web history routing. Run through
// scripts/verify-web-history.sh, which builds and serves the app and puts
// Playwright on NODE_PATH.
//
// Real clicks, and history.back()/forward() through page.evaluate: page.goBack()
// waits for a navigation and hides what a user's Back button actually does.
//
// Usage: verify-web-history.cjs <pagesUrl> <rootUrl>
const {chromium} = require('playwright');

const PAGES_APP = '/mobadex/app/';
const LANDING = '/mobadex/';
const TIMEOUT_MS = 8000;

const HEROES = [
  {id: 2, name: 'Axe', npc: 'axe', attr: 'str', roles: ['Initiator', 'Durable']},
  {id: 5, name: 'Crystal Maiden', npc: 'crystal_maiden', attr: 'int', roles: ['Support', 'Nuker']},
  {id: 8, name: 'Juggernaut', npc: 'juggernaut', attr: 'agi', roles: ['Carry', 'Pusher']},
  {id: 74, name: 'Invoker', npc: 'invoker', attr: 'all', roles: ['Carry', 'Nuker']},
].map(hero => ({...hero, card: new RegExp(`^${hero.name}, `)}));
const [AXE, MAIDEN, JUGGERNAUT] = HEROES;

const heroesResponse = HEROES.map(hero => ({
  id: hero.id,
  name: `npc_dota_hero_${hero.npc}`,
  localized_name: hero.name,
  primary_attr: hero.attr,
  attack_type: 'Melee',
  roles: hero.roles,
  legs: 2,
}));

const detailMarker = hero => `Fixture ability of ${hero.name}`;

const heroDetailsResponse = hero => ({
  result: {
    data: {
      heroes: [
        {
          id: hero.id,
          name: `npc_dota_hero_${hero.npc}`,
          name_loc: hero.name,
          bio_loc: 'Fixture lore.',
          hype_loc: 'Fixture hype.',
          str_base: 20,
          str_gain: 2,
          agi_base: 20,
          agi_gain: 2,
          int_base: 20,
          int_gain: 2,
          primary_attr: 0,
          complexity: 1,
          damage_min: 50,
          damage_max: 60,
          armor: 2,
          attack_rate: 1.7,
          attack_range: 150,
          magic_resistance: 25,
          movement_speed: 300,
          sight_range_day: 1800,
          sight_range_night: 800,
          max_health: 600,
          health_regen: 2,
          max_mana: 300,
          mana_regen: 1,
          abilities: [
            {
              id: hero.id * 100,
              name: `${hero.npc}_fixture`,
              name_loc: detailMarker(hero),
              desc_loc: 'Fixture description.',
              type: 0,
              cooldowns: [10],
              mana_costs: [50],
              ability_is_innate: false,
              is_item: false,
            },
          ],
        },
      ],
    },
  },
});

// Inactive screens stay mounted, so a screen only counts when its marker is
// shown and the markers of the others are not.
const SCREEN_MARKERS = {
  Home: 'Dota 2 Heroes',
  Explore: 'Filter the roster by attribute and role.',
  Superstar: 'HERO OF THE DAY',
};

const poll = async (describeState, isDone, what) => {
  const deadline = Date.now() + TIMEOUT_MS;
  for (;;) {
    if (await isDone()) {
      return;
    }
    if (Date.now() > deadline) {
      throw new Error(`${what}; found ${await describeState()}`);
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
};

const urlOf = target =>
  target.evaluate(() => location.pathname + location.search + location.hash);

const expectUrl = (target, expected) =>
  poll(
    () => urlOf(target),
    async () => (await urlOf(target)) === expected,
    `expected the URL ${expected}`,
  );

// Inactive tabs keep their layout behind the active one, so Playwright calls
// them visible; react-navigation marks them aria-hidden.
const isTextVisible = (target, text) =>
  target
    .getByText(text, {exact: true})
    .filter({visible: true})
    .evaluateAll(elements =>
      elements.some(element => !element.closest('[aria-hidden="true"]')),
    );

const visibleScreens = async target => {
  const visible = [];
  const markers = [
    ...Object.entries(SCREEN_MARKERS),
    ...HEROES.map(hero => [`Detail(${hero.name})`, detailMarker(hero)]),
  ];
  for (const [name, marker] of markers) {
    if (await isTextVisible(target, marker)) {
      visible.push(name);
    }
  }
  return visible.join('+') || 'no screen';
};

const expectScreen = (target, name) =>
  poll(
    () => visibleScreens(target),
    async () => (await visibleScreens(target)) === name,
    `expected the screen ${name}`,
  );

// The URL and the screen must agree after every step.
const expectAt = async (target, url, screen) => {
  await expectUrl(target, url);
  await expectScreen(target, screen);
};

const expectDetail = (target, url, hero) =>
  expectAt(target, url, `Detail(${hero.name})`);

const expectCount = async (target, label) => {
  await poll(
    () => target.locator('body').innerText(),
    () => isTextVisible(target, label),
    `expected the count "${label}"`,
  );
};

const clickVisible = locator => locator.filter({visible: true}).first().click();
const clickTab = (target, name) =>
  clickVisible(target.getByRole('tab', {name: new RegExp(`${name}$`)}));
const clickHero = (target, hero) =>
  clickVisible(target.getByRole('button', {name: hero.card}));
const clickChevron = target =>
  clickVisible(target.getByRole('button', {name: 'Go back', exact: true}));

const back = page => page.evaluate(() => history.back());
const forward = page => page.evaluate(() => history.forward());

const scenarioA = async ({page, open, base}) => {
  await open(base);
  await expectAt(page, base, 'Home');
  await expectCount(page, `${HEROES.length} heroes`);

  const search = page.getByPlaceholder('Search by name or role');
  await search.fill('axe');
  await expectCount(page, '1 hero');
  if (await isTextVisible(page, '1 heroes')) {
    throw new Error('the count still reads "1 heroes"');
  }

  const detailUrl = `${base}?/hero/${AXE.id}`;
  await clickHero(page, AXE);
  await expectDetail(page, detailUrl, AXE);

  await back(page);
  await expectAt(page, base, 'Home');
  const kept = await search.inputValue();
  if (kept !== 'axe') {
    throw new Error(`the search box holds "${kept}" after Back, expected "axe"`);
  }
  if (page.url() === 'about:blank') {
    throw new Error('Back left the app for about:blank');
  }

  await forward(page);
  await expectDetail(page, detailUrl, AXE);
};

const scenarioB = async ({page, open, base}) => {
  await open(base);
  await expectAt(page, base, 'Home');

  await clickTab(page, 'Explore');
  await expectAt(page, `${base}?/explore`, 'Explore');
  await clickVisible(page.getByRole('button', {name: 'Intelligence', exact: true}));
  await expectCount(page, '1 hero');

  await clickTab(page, 'Superstar');
  await expectAt(page, `${base}?/superstar`, 'Superstar');
  await clickTab(page, 'Home');
  await expectAt(page, base, 'Home');

  await back(page);
  await expectAt(page, `${base}?/superstar`, 'Superstar');
  await back(page);
  await expectAt(page, `${base}?/explore`, 'Explore');
  await back(page);
  await expectAt(page, base, 'Home');

  await forward(page);
  await expectAt(page, `${base}?/explore`, 'Explore');
};

const scenarioC = async ({page, open, base}) => {
  await open(base);
  await clickTab(page, 'Explore');
  await expectAt(page, `${base}?/explore`, 'Explore');

  const detailUrl = `${base}?/hero/${MAIDEN.id}`;
  await clickHero(page, MAIDEN);
  await expectDetail(page, detailUrl, MAIDEN);

  await clickChevron(page);
  await expectAt(page, `${base}?/explore`, 'Explore');

  await forward(page);
  await expectDetail(page, detailUrl, MAIDEN);
};

const scenarioD = async ({page, open, base, dataRequests}) => {
  const detailUrl = `${base}?/hero/${JUGGERNAUT.id}`;
  await open(detailUrl);
  await expectDetail(page, detailUrl, JUGGERNAUT);

  const reloaded = await page.reload();
  if (reloaded.status() !== 200) {
    throw new Error(`reload answered HTTP ${reloaded.status()}, expected 200`);
  }
  await expectDetail(page, detailUrl, JUGGERNAUT);

  const expected = `${base}data/heroes/${JUGGERNAUT.id}.json`;
  if (!dataRequests.includes(expected)) {
    throw new Error(`no request for ${expected}; saw ${dataRequests.join(', ')}`);
  }
  const outside = dataRequests.filter(url => !url.startsWith(`${base}data/heroes/`));
  if (outside.length) {
    throw new Error(`data requests outside the base path: ${outside.join(', ')}`);
  }

  await clickChevron(page);
  await expectAt(page, base, 'Home');
};

const scenarioE = async ({page, open, base}) => {
  await open(base);
  await clickTab(page, 'Explore');
  await expectAt(page, `${base}?/explore`, 'Explore');

  const detailUrl = `${base}?/hero/${MAIDEN.id}`;
  await clickHero(page, MAIDEN);
  await expectDetail(page, detailUrl, MAIDEN);

  await page.reload();
  await expectDetail(page, detailUrl, MAIDEN);

  await back(page);
  await expectAt(page, `${base}?/explore`, 'Explore');
};

const scenarioF = async ({page, open}) => {
  await open(LANDING);
  const element = await page.waitForSelector('iframe[title^="MobaDex"]');
  const app = await element.contentFrame();

  const expectIframe = async check => {
    await check();
    const top = await urlOf(page);
    if (top !== LANDING) {
      throw new Error(`the top frame moved to ${top}, expected ${LANDING}`);
    }
  };
  const home = () => expectAt(app, PAGES_APP, 'Home');
  const explore = () => expectAt(app, `${PAGES_APP}?/explore`, 'Explore');
  const detail = () => expectDetail(app, `${PAGES_APP}?/hero/${AXE.id}`, AXE);

  await expectIframe(home);

  await clickHero(app, AXE);
  await expectIframe(detail);
  await back(page);
  await expectIframe(home);
  await forward(page);
  await expectIframe(detail);
  await back(page);
  await expectIframe(home);

  await clickTab(app, 'Explore');
  await expectIframe(explore);
  await back(page);
  await expectIframe(home);
  await forward(page);
  await expectIframe(explore);
};

const runScenario = async (browser, {origin, base, viewport, run, landing}) => {
  const context = await browser.newContext({viewport});
  const dataRequests = [];

  // Nothing leaves the machine: the hero data is mocked, the rest is aborted.
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) {
      const heroFile = url.pathname.match(/data\/heroes\/(\d+)\.json$/);
      if (!heroFile) {
        return route.continue();
      }
      dataRequests.push(url.pathname);
      const hero = HEROES.find(item => item.id === Number(heroFile[1]));
      return hero && url.pathname.startsWith(base)
        ? route.fulfill({json: heroDetailsResponse(hero)})
        : route.fulfill({status: 404});
    }
    if (url.hostname === 'api.opendota.com' && url.pathname === '/api/heroes') {
      return route.fulfill({
        json: heroesResponse,
        headers: {'access-control-allow-origin': '*'},
      });
    }
    return route.abort();
  });

  const page = await context.newPage();
  const crashes = [];
  const written = [];
  page.on('pageerror', error => crashes.push(error.message));
  page.on('framenavigated', frame => {
    // Scenario F checks the landing page's own URL after every step.
    if (landing && frame === page.mainFrame()) {
      return;
    }
    const {origin: frameOrigin, pathname, search, hash} = new URL(frame.url());
    if (frameOrigin === origin && !pathname.includes('/viewer/')) {
      written.push(pathname + search + hash);
    }
  });

  const open = async path => {
    const response = await page.goto(origin + path);
    if (response.status() !== 200) {
      throw new Error(`${path} answered HTTP ${response.status()}, expected 200`);
    }
  };

  try {
    await run({page, open, base, dataRequests});
    if (crashes.length) {
      throw new Error(`uncaught page errors: ${crashes.join('; ')}`);
    }
    const allowed = new RegExp(
      `^${base}(\\?/(explore|superstar|settings|hero/\\d+))?$`,
    );
    const stray = written.filter(url => !allowed.test(url));
    if (stray.length) {
      throw new Error(`URLs outside the format were written: ${stray.join(', ')}`);
    }
  } finally {
    await context.close();
  }
};

const main = async () => {
  const [pagesUrl, rootUrl] = process.argv.slice(2);
  if (!pagesUrl || !rootUrl) {
    throw new Error('usage: verify-web-history.cjs <pagesUrl> <rootUrl>');
  }

  const phone = {width: 390, height: 844};
  const desktop = {width: 1440, height: 1100};
  const appScenarios = [
    ['A', 'search, open a hero, Back keeps the search, Forward', scenarioA],
    ['B', 'Explore filter count, tab history Back x3, Forward', scenarioB],
    ['C', 'detail from Explore, chevron, Forward reopens it', scenarioC],
    ['D', 'deep link and reload, data under the base, chevron to Home', scenarioD],
    ['E', 'Home, Explore, detail, reload, Back to Explore', scenarioE],
  ];
  const cases = [];
  for (const [origin, base] of [
    [pagesUrl, PAGES_APP],
    [rootUrl, '/'],
  ]) {
    for (const [id, title, run] of appScenarios) {
      cases.push({id, title, origin, base, run, viewport: phone});
    }
  }
  cases.push({
    id: 'F',
    title: 'landing iframe, top-frame Back and Forward',
    origin: pagesUrl,
    base: PAGES_APP,
    run: scenarioF,
    landing: true,
    viewport: desktop,
  });

  const browser = await chromium.launch({channel: 'chromium', headless: true});
  let failed = 0;
  try {
    for (const item of cases) {
      const label = `${item.id} at ${item.id === 'F' ? LANDING : item.base}: ${item.title}`;
      try {
        await runScenario(browser, item);
        console.log(`PASS ${label}`);
      } catch (error) {
        failed += 1;
        console.log(`FAIL ${label}\n     ${error.message}`);
      }
    }
  } finally {
    await browser.close();
  }

  console.log(`${cases.length - failed}/${cases.length} scenarios passed`);
  process.exitCode = failed ? 1 : 0;
};

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
