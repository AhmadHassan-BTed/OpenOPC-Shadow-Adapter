import React, { useState } from 'react';
import { api } from '../api/client';
import { ContractorPublic } from '../types';
import { Lock, User, AlertCircle, Layers } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess: (contractor: ContractorPublic) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegistering) {
        await api.register(username, password, email || undefined);
        // Auto-login after registration
        const loginRes = await api.login(username, password);
        onLoginSuccess(loginRes.contractor);
      } else {
        const loginRes = await api.login(username, password);
        onLoginSuccess(loginRes.contractor);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-opc-bg px-4">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-opc-accent/15 border border-opc-accent/30 text-opc-accent mb-2">
            <Layers className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-opc-text tracking-tight">
            {isRegistering ? 'Create Contractor Account' : 'Sign in to Shadow Portal'}
          </h2>
          <p className="text-xs text-opc-text-secondary">
            Human-in-the-Loop Deliverable Management for OpenOPC DAGs
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-opc-elevated border border-opc-border rounded-opc p-6 space-y-4 shadow-xl">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-opc-sm text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-opc-text-secondary mb-1">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-opc-text-dim absolute left-3 top-3" />
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="contractor_user"
                className="w-full pl-9 pr-3 py-2 bg-opc-secondary border border-opc-border rounded-opc-sm text-xs text-opc-text placeholder:text-opc-text-dim focus:outline-none focus:border-opc-accent transition-colors"
              />
            </div>
          </div>

          {isRegistering && (
            <div>
              <label className="block text-xs font-medium text-opc-text-secondary mb-1">Email (Optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="contractor@example.com"
                className="w-full px-3 py-2 bg-opc-secondary border border-opc-border rounded-opc-sm text-xs text-opc-text placeholder:text-opc-text-dim focus:outline-none focus:border-opc-accent transition-colors"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-opc-text-secondary mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-opc-text-dim absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 bg-opc-secondary border border-opc-border rounded-opc-sm text-xs text-opc-text placeholder:text-opc-text-dim focus:outline-none focus:border-opc-accent transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-opc-accent hover:bg-opc-accent-hover text-white text-xs font-semibold rounded-opc-sm transition-colors shadow-lg shadow-opc-accent/20 disabled:opacity-50"
          >
            {loading ? 'Processing...' : isRegistering ? 'Register Account' : 'Sign In'}
          </button>

          <div className="pt-2 text-center">
            <button
              type="button"
              onClick={() => {
                setIsRegistering(!isRegistering);
                setError(null);
              }}
              className="text-xs text-opc-text-secondary hover:text-opc-accent transition-colors"
            >
              {isRegistering ? 'Already have an account? Sign In' : 'Need an account? Register'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
