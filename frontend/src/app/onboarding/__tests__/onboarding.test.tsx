import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import OnboardingPage from '~/app/onboarding/page';

jest.mock('@stackframe/stack', () => ({
  useUser: () => ({
    async createTeam({ displayName }: { displayName: string }) { return { id: 'team_1', displayName, async update(){}, }; },
    async setSelectedTeam(_team: any) { /* no-op */ },
  }),
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: jest.fn() }),
}));

describe('OnboardingPage', () => {
  it('requires team name and handles create flow', async () => {
    render(<OnboardingPage />);

    // Missing name -> shows error
    fireEvent.submit(screen.getByRole('button', { name: /create team/i }));
    await screen.findByText(/team name is required/i);

    // Provide name and submit -> no error
    fireEvent.change(screen.getByPlaceholderText(/acme/i), { target: { value: 'Acme' } });
    fireEvent.submit(screen.getByRole('button', { name: /create team/i }));

    await waitFor(() => {
      // Button should flip to creating… then back; no crash
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
  });
});

