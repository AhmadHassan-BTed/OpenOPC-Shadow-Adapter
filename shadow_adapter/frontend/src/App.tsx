import React, { useEffect, useState } from 'react';
import { api } from './api/client';
import { ContractorPublic } from './types';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { TaskDetailPage } from './pages/TaskDetailPage';

export const App: React.FC = () => {
  const [contractor, setContractor] = useState<ContractorPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('shadow_token');
      if (token) {
        try {
          const user = await api.getMe();
          setContractor(user);
        } catch (err) {
          api.clearToken();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const handleLoginSuccess = (user: ContractorPublic) => {
    setContractor(user);
    setSelectedTaskId(null);
  };

  const handleLogout = () => {
    api.clearToken();
    setContractor(null);
    setSelectedTaskId(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-opc-bg flex items-center justify-center text-opc-text-secondary text-sm">
        Initializing Shadow Portal...
      </div>
    );
  }

  if (!contractor) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <Layout contractor={contractor} onLogout={handleLogout}>
      {selectedTaskId ? (
        <TaskDetailPage
          taskId={selectedTaskId}
          contractor={contractor}
          onBack={() => setSelectedTaskId(null)}
        />
      ) : (
        <DashboardPage
          contractor={contractor}
          onSelectTask={(id) => setSelectedTaskId(id)}
        />
      )}
    </Layout>
  );
};

export default App;
