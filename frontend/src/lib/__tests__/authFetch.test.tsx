import { renderHook, act } from '@testing-library/react';
import { useAuthFetch } from '~/lib/authFetch';

// Minimal mock for @stackframe/stack useUser
jest.mock('@stackframe/stack', () => ({
  useUser: () => ({
    async getAuthJson() { return { accessToken: 'test-token' }; },
  }),
}));

describe('useAuthFetch', () => {
  it('attaches Authorization header by default', async () => {
    const { result } = renderHook(() => useAuthFetch());

    const mockFetch = jest.fn(async () => ({ ok: true })) as any;
    const origFetch = global.fetch;
    (global as any).fetch = mockFetch;

    await act(async () => {
      await result.current('https://example.com/api', { method: 'GET' });
    });

    expect(mockFetch).toHaveBeenCalled();
    const headers = mockFetch.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer test-token');

    (global as any).fetch = origFetch;
  });

  it('skips auth when auth:false', async () => {
    const { result } = renderHook(() => useAuthFetch());

    const mockFetch = jest.fn(async () => ({ ok: true })) as any;
    const origFetch = global.fetch;
    (global as any).fetch = mockFetch;

    await act(async () => {
      await result.current('https://example.com/open', { method: 'GET', auth: false });
    });

    expect(mockFetch).toHaveBeenCalled();
    const headers = (mockFetch.mock.calls[0][1].headers || {}) as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();

    (global as any).fetch = origFetch;
  });
});

