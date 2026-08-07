const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  user: AuthUser;
  access_token: string;
  refresh_token: string;
}

class AuthClient {
  async login(email: string, password: string, remember_me: boolean = false): Promise<AuthResponse> {
    if (!email || !password) {
      throw new Error("Email and password are required");
    }
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, remember_me }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    return data;
  }

  async register(name: string, email: string, password: string): Promise<AuthResponse> {
    if (!name || !email || !password) {
      throw new Error("All fields are required");
    }
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    return data;
  }

  async forgotPassword(email: string): Promise<{ message: string }> {
    if (!email) throw new Error("Email is required");
    const res = await fetch(`${API_BASE}/api/v1/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  }

  async resetPassword(token: string, new_password: string): Promise<{ message: string }> {
    if (!token || !new_password) throw new Error("Token and password are required");
    const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Reset password failed");
    return data;
  }

  async refreshToken(refresh_token: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Token refresh failed");
    return data;
  }
}

export const authClient = new AuthClient();
