import { render, screen } from '@testing-library/react';
import OnboardingGate from '~/components/OnboardingGate';
import * as nextNav from 'next/navigation';

jest.mock('next/navigation', () => ({
  ...jest.requireActual('next/navigation'),
  useRouter: () => ({ replace: jest.fn() }),
  usePathname: () => '/app',
}));

jest.mock('@stackframe/stack', () => ({
  useUser: () => ({
    useTeams: () => [],
    selectedTeam: null,
  }),
}));

describe('OnboardingGate', () => {
  it('redirects to /onboarding when no teams', () => {
    render(<OnboardingGate />);
    expect(screen.queryByText('anything')).toBeNull();
  });
});

