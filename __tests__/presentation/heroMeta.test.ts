import {heroCountLabel} from '../../src/presentation/theme/heroMeta';

describe('heroCountLabel', () => {
  it('pluralizes zero', () => {
    expect(heroCountLabel(0)).toBe('0 heroes');
  });

  it('uses the singular for exactly one', () => {
    expect(heroCountLabel(1)).toBe('1 hero');
  });

  it('pluralizes two', () => {
    expect(heroCountLabel(2)).toBe('2 heroes');
  });

  it('pluralizes a full roster', () => {
    expect(heroCountLabel(126)).toBe('126 heroes');
  });
});
