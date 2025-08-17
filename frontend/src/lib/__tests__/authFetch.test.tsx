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

  it('attaches X-Team-Id from selectedTeam when not explicitly provided', async () => {
    jest.resetModules();
    jest.doMock('@stackframe/stack', () => ({
      useUser: () => ({
        async getAuthJson() { return { accessToken: 'test-token' }; },
        selectedTeam: { id: 'team-abc' },
      }),
    }));
    const { useAuthFetch: useAuthFetchReloaded } = await import('~/lib/authFetch');
    const { result } = renderHook(() => useAuthFetchReloaded());

    const mockFetch = jest.fn(async () => ({ ok: true })) as any;
    const origFetch = global.fetch;
    (global as any).fetch = mockFetch;

    await act(async () => {
      await result.current('https://example.com/api', { method: 'GET' });
    });
    const headers = mockFetch.mock.calls[0][1].headers as Record<string, string>;
    expect(headers['X-Team-Id']).toBe('team-abc');

    (global as any).fetch = origFetch;
    jest.dontMock('@stackframe/stack');
  });

  it('prefers explicit teamId over selectedTeam', async () => {
    jest.resetModules();
    jest.doMock('@stackframe/stack', () => ({
      useUser: () => ({
        async getAuthJson() { return { accessToken: 'test-token' }; },
        selectedTeam: { id: 'team-abc' },
      }),
    }));
    const { useAuthFetch: useAuthFetchReloaded } = await import('~/lib/authFetch');
    const { result } = renderHook(() => useAuthFetchReloaded());

    const mockFetch = jest.fn(async () => ({ ok: true })) as any;
    const origFetch = global.fetch;
    (global as any).fetch = mockFetch;

    await act(async () => {
      await result.current('https://example.com/api', { method: 'GET', teamId: 'team-xyz' } as any);
    });
    const headers = mockFetch.mock.calls[0][1].headers as Record<string, string>;
    expect(headers['X-Team-Id']).toBe('team-xyz');

    (global as any).fetch = origFetch;
    jest.dontMock('@stackframe/stack');
  });

  it('does not attach Authorization when auth=false', async () => {
    const { result } = renderHook(() => useAuthFetch());
    const mockFetch = jest.fn(async () => ({ ok: true })) as any;
    const origFetch = global.fetch;
    (global as any).fetch = mockFetch;

    await act(async () => {
      await result.current('https://example.com/api', { method: 'GET', auth: false } as any);
    });

    const initArg = mockFetch.mock.calls[0][1] as RequestInit;
    const headers = initArg.headers as Record<string, string> | undefined;
    expect(headers?.Authorization).toBeUndefined();

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

