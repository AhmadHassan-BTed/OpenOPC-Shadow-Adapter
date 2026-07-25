import React, { useState, useEffect } from 'react';
import { ContractorPublic } from '../types';
import { LogOut, User, Layers, Sun, Moon } from 'lucide-react';

interface LayoutProps {
  contractor: ContractorPublic | null;
  onLogout: () => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ contractor, onLogout, children }) => {
  const [isLightMode, setIsLightMode] = useState(() => {
    return localStorage.getItem('shadow_theme') === 'light';
  });

  useEffect(() => {
    if (isLightMode) {
      document.documentElement.classList.add('light-theme');
      localStorage.setItem('shadow_theme', 'light');
    } else {
      document.documentElement.classList.remove('light-theme');
      localStorage.setItem('shadow_theme', 'dark');
    }
  }, [isLightMode]);

  const toggleTheme = () => {
    setIsLightMode((prev) => !prev);
  };

  return (
    <div className="min-h-screen flex flex-col bg-opc-bg text-opc-text transition-colors duration-200">
      {/* Top Navbar */}
      <header className="h-14 border-b border-opc-border bg-opc-elevated/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-opc-sm bg-opc-accent/20 border border-opc-accent/40 flex items-center justify-center text-opc-accent">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-opc-text flex items-center space-x-1.5">
              <span>OpenOPC</span>
              <span className="text-opc-accent font-bold px-1.5 py-0.2 bg-opc-accent-soft rounded text-xs">
                Contractor Portal
              </span>
            </h1>
            <p className="text-[10px] text-opc-text-dim">Human-in-the-Loop & BYOC Workspace</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Dark / Light Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 text-opc-text-secondary hover:text-opc-text hover:bg-opc-secondary border border-opc-border rounded-opc-sm transition-colors flex items-center space-x-1.5 text-xs"
            title="Toggle Light/Dark Theme"
          >
            {isLightMode ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5 text-amber-400" />}
          </button>

          {contractor && (
            <div className="flex items-center space-x-3">
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
                className="p-2 text-opc-text-secondary hover:text-rose-400 hover:bg-rose-500/10 border border-opc-border rounded-opc-sm transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Body */}
      <main className="flex-1">{children}</main>
    </div>
  );
};
