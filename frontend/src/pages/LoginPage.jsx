import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/useAuthStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await authApi.login(email, password);
      // Store token first so the /me call can use it in the Authorization header
      setAuth({ token: data.access_token, refreshToken: data.refresh_token, user: null });
      const me = await authApi.me();
      setAuth({ token: data.access_token, refreshToken: data.refresh_token, user: me });
      navigate('/');
    } catch (err) {
      setError(err.body?.detail || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--color-bg)',
    }}>
      <div style={{ width: '100%', maxWidth: 400, padding: '0 24px' }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <h1 style={{
            fontSize: 32, fontWeight: 800,
            background: 'linear-gradient(135deg, var(--color-primary-light), var(--color-accent))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            Warehaven
          </h1>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, marginTop: 6 }}>
            AI-Assisted Warehouse Slotting Optimization
          </p>
        </div>

        {/* Login card */}
        <div className="card" style={{ padding: '32px 28px' }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 24 }}>Sign in</h2>

          {error && (
            <div style={{
              background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)',
              borderRadius: 8, padding: '10px 14px', marginBottom: 20,
              color: 'var(--color-danger)', fontSize: 13,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="admin@warehaven.local"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button
              id="login-submit"
              type="submit"
              className="btn btn-primary w-full"
              style={{ marginTop: 8, justifyContent: 'center' }}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
