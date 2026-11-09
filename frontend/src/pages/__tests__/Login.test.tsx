import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Login from '../Login'
import * as authApi from '../../api/auth'
import { setTokens } from '../../api/client'

vi.mock('../../api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  setTokens: vi.fn(),
}))

const mockedLogin = vi.mocked(authApi.login)
const mockedRegister = vi.mocked(authApi.register)

function renderLogin(initialEntries = ['/login']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Login />
    </MemoryRouter>
  )
}

const authResponse = {
  access_token: 'access-1',
  token_type: 'Bearer',
  expires_in: 900,
  refresh_token: 'refresh-1',
}

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('renders the login form by default', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create one/i })).toBeInTheDocument()
  })

  it('submits login with email and password', async () => {
    const user = userEvent.setup()
    mockedLogin.mockResolvedValue(authResponse)
    renderLogin()

    await user.type(screen.getByLabelText(/email/i), 'jane@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockedLogin).toHaveBeenCalledWith('jane@example.com', 'password123')
    })
    expect(setTokens).toHaveBeenCalledWith('access-1', 'refresh-1')
  })

  it('shows a backend error message on failed login', async () => {
    const user = userEvent.setup()
    mockedLogin.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid email or password' } },
    })
    renderLogin()

    await user.type(screen.getByLabelText(/email/i), 'jane@example.com')
    await user.type(screen.getByLabelText(/password/i), 'wrong')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
    })
    expect(setTokens).not.toHaveBeenCalled()
  })

  it('toggles to register mode', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByRole('button', { name: /create one/i }))

    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in$/i })).toBeInTheDocument()
  })

  it('submits registration with email and password', async () => {
    const user = userEvent.setup()
    mockedRegister.mockResolvedValue(authResponse)
    renderLogin()

    await user.click(screen.getByRole('button', { name: /create one/i }))
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockedRegister).toHaveBeenCalledWith('new@example.com', 'password123')
    })
    expect(setTokens).toHaveBeenCalledWith('access-1', 'refresh-1')
  })

  it('shows a backend error message on failed registration', async () => {
    const user = userEvent.setup()
    mockedRegister.mockRejectedValue({
      response: { status: 400, data: { detail: 'Email already registered' } },
    })
    renderLogin()

    await user.click(screen.getByRole('button', { name: /create one/i }))
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/email already registered/i)).toBeInTheDocument()
    })
    expect(setTokens).not.toHaveBeenCalled()
  })

  it('renders a readable message on FastAPI 422 validation errors (detail is an array)', async () => {
    const user = userEvent.setup()
    mockedRegister.mockRejectedValue({
      response: {
        status: 422,
        data: {
          detail: [
            {
              type: 'string_too_short',
              loc: ['body', 'password'],
              msg: 'String should have at least 8 characters',
              input: 'Test!!1',
              ctx: { min_length: 8 },
            },
          ],
        },
      },
    })
    renderLogin()

    await user.click(screen.getByRole('button', { name: /create one/i }))
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
    })
    // The error must be text, not an object — React would crash rendering an array
    expect(screen.getByText(/password must be at least 8 characters/i).textContent).not.toContain('[object')
  })

  it('blocks submission client-side when the password is under 8 characters', async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByRole('button', { name: /create one/i }))
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/password/i), 'Test!!1')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockedRegister).not.toHaveBeenCalled()
    expect(screen.getByText(/password must be at least 8 characters \(you entered 7\)/i)).toBeInTheDocument()
    expect(screen.getByText(/1 more character needed/i)).toBeInTheDocument()
  })
})
