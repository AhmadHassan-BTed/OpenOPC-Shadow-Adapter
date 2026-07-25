import React from 'react';
import { ContractorPublic } from '../types';
import { LogOut, User, CheckSquare, Layers } from 'lucide-react';

interface LayoutProps {
  contractor: ContractorPublic | null;
  onLogout: () => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ contractor, onLogout, children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-opc-bg text-opc-text">
      {/* Top Navbar */}
      <header className="h-14 border-b border-opc-border bg-opc-elevated/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-opc-sm bg-opc-accent/20 border border-opc-accent/40 flex items-center justify-center text-opc-accent">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-opc-text">
              OpenOPC <span className="text-opc-accent font-bold">Shadow Portal</span>
            </h1>
            <p className="text-[10px] text-opc-text-dim">Human-in-the-Loop Orchestration</p>
          </div>
        </div>

        {contractor && (
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-1 bg-opc-secondary border border-opc-border rounded-full text-xs">
              <User className="w-3.5 h-3.5 text-opc-accent" />
              <span className="font-medium text-opc-text">{contractor.display_name || contractor.username}</span>
              {contractor.roles.includes('admin') && (
                <span className="text-[10px] px-1.5 py-0.2 bg-opc-accent-soft text-opc-accent rounded font-semibold uppercase">
                  Admin
                </span>
              )}
            </div>

            <button
              onClick={onLogout}
              className="p-1.5 text-opc-text-secondary hover:text-rose-400 hover:bg-rose-500/10 rounded-opc-sm transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="py-4 border-t border-opc-border text-center text-xs text-opc-text-dim">
        OpenOPC Shadow Adapter v0.1.0 — Isolated State WAL Engine
      </footer>
    </div>
  );
};
