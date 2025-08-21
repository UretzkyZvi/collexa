import * as nextNav from 'next/navigation';

export function mockNextNavigation(overrides?: Partial<Record<keyof typeof nextNav, any>>) {
  ;(nextNav as any).useRouter = () => ({
    replace: jest.fn(),
    push: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  } as any);
  ;(nextNav as any).useSearchParams = () => ({
    get: jest.fn().mockReturnValue(null),
    toString: () => '',
    entries: function* () {},
    forEach: () => {},
    getAll: () => [],
    has: () => false,
    keys: function* () {},
    values: function* () {},
    [Symbol.iterator]: function* () {},
  } as any);
  if (overrides) {
    for (const [k, v] of Object.entries(overrides)) {
      jest.spyOn(nextNav as any, k).mockReturnValue(v);
    }
  }
}

