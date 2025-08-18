import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SettingsPage from "../page";

// Mock useAuthFetch
const mockAuthFetch = jest.fn();
jest.mock("@/hooks/useAuthFetch", () => ({
  useAuthFetch: () => mockAuthFetch,
}));

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn(),
  },
});

describe("SettingsPage", () => {
  beforeEach(() => {
    mockAuthFetch.mockClear();
    (navigator.clipboard.writeText as jest.Mock).mockClear();
  });

  it("renders settings page with API keys section", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: "agent-1", display_name: "Test Agent 1" },
        { id: "agent-2", display_name: "Test Agent 2" },
      ],
    });

    render(<SettingsPage />);

    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("API Keys")).toBeInTheDocument();
    expect(screen.getByText(/Create API keys to access your agents/)).toBeInTheDocument();

    // Wait for agents to load
    await waitFor(() => {
      expect(screen.getByText("Test Agent 1")).toBeInTheDocument();
    });
  });

  it("creates API key when form is submitted", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "agent-1", display_name: "Test Agent" }],
    });

    // Mock API key creation response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        key_id: "key-123",
        api_key: "test-api-key-value",
      }),
    });

    render(<SettingsPage />);

    // Wait for agents to load
    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    // Fill in key name
    const keyNameInput = screen.getByPlaceholderText(/e.g., Production Key/);
    fireEvent.change(keyNameInput, { target: { value: "Test Key" } });

    // Click create button
    const createButton = screen.getByText("Create Key");
    fireEvent.click(createButton);

    // Wait for API key to be created and displayed
    await waitFor(() => {
      expect(screen.getByText("New API Key Created")).toBeInTheDocument();
      expect(screen.getByText("test-api-key-value")).toBeInTheDocument();
    });

    // Verify API call was made
    expect(mockAuthFetch).toHaveBeenCalledWith("/v1/agents/agent-1/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Test Key" }),
    });
  });

  it("copies API key to clipboard", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "agent-1", display_name: "Test Agent" }],
    });

    // Mock API key creation response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        key_id: "key-123",
        api_key: "test-api-key-value",
      }),
    });

    // Mock alert
    window.alert = jest.fn();

    render(<SettingsPage />);

    // Wait for agents to load and create a key
    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    const createButton = screen.getByText("Create Key");
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText("New API Key Created")).toBeInTheDocument();
    });

    // Click copy button
    const copyButton = screen.getByText("Copy");
    fireEvent.click(copyButton);

    // Verify clipboard was called
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("test-api-key-value");
    expect(window.alert).toHaveBeenCalledWith("Copied to clipboard!");
  });

  it("shows usage instructions", () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    render(<SettingsPage />);

    expect(screen.getByText("Using API Keys")).toBeInTheDocument();
    expect(screen.getByText("HTTP Requests")).toBeInTheDocument();
    expect(screen.getByText("n8n Integration")).toBeInTheDocument();
    expect(screen.getByText(/curl -X POST/)).toBeInTheDocument();
  });

  it("handles API key creation error", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "agent-1", display_name: "Test Agent" }],
    });

    // Mock failed API key creation
    mockAuthFetch.mockResolvedValueOnce({
      ok: false,
    });

    // Mock alert
    window.alert = jest.fn();

    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Test Agent")).toBeInTheDocument();
    });

    const keyNameInput = screen.getByPlaceholderText(/e.g., Production Key/);
    fireEvent.change(keyNameInput, { target: { value: "Test Key" } });

    const createButton = screen.getByText("Create Key");
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith("Failed to create API key");
    });
  });
});
