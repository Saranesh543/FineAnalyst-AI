export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatar: string;
}

export interface AuthResponse {
  user: AuthUser;
  accessToken: string;
}

class AuthClient {
  private async delay(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    await this.delay(800); // Simulate network latency

    if (!email || !password) {
      throw new Error("Email and password are required");
    }

    // Mock successful login
    return {
      user: {
        id: "usr_" + Math.random().toString(36).substr(2, 9),
        name: email.split('@')[0] || "Saran",
        email: email,
        avatar: email.charAt(0).toUpperCase()
      },
      accessToken: "mock_token_" + Date.now().toString()
    };
  }

  async register(name: string, email: string, password: string): Promise<AuthResponse> {
    await this.delay(1000); // Simulate network latency

    if (!name || !email || !password) {
      throw new Error("All fields are required");
    }

    return {
      user: {
        id: "usr_" + Math.random().toString(36).substr(2, 9),
        name: name,
        email: email,
        avatar: name.charAt(0).toUpperCase()
      },
      accessToken: "mock_token_" + Date.now().toString()
    };
  }

  async forgotPassword(email: string): Promise<{ success: boolean; message: string }> {
    await this.delay(800); // Simulate network latency

    if (!email) {
      throw new Error("Email is required");
    }

    return {
      success: true,
      message: "If an account exists, a reset link has been sent."
    };
  }
}

export const authClient = new AuthClient();
