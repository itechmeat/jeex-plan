import React from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { Layout } from './components/Layout/Layout';
import { ProjectWizard } from './components/ProjectWizard/ProjectWizard';
import { ProtectedRoute } from './components/ProtectedRoute';
import { PublicRoute } from './components/PublicRoute';
import { AuthProvider } from './contexts/AuthContext';
import { Dashboard } from './pages/Dashboard/Dashboard';
import HealthStatus from './pages/HealthStatus/HealthStatus';
import { Login } from './pages/Login/Login';
import { Projects } from './pages/Projects/Projects';
import { Register } from './pages/Register/Register';
import { DBProvider } from './providers/DBProvider';

const App: React.FC = () => {
  return (
    <DBProvider>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public Routes */}
            <Route
              path='/login'
              element={
                <PublicRoute>
                  <Login />
                </PublicRoute>
              }
            />
            <Route
              path='/register'
              element={
                <PublicRoute>
                  <Register />
                </PublicRoute>
              }
            />

            {/* Protected Routes */}
            <Route
              path='/'
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to='/dashboard' replace />} />
              <Route path='dashboard' element={<Dashboard />} />
              <Route path='projects' element={<Projects />} />
              <Route path='projects/new' element={<ProjectWizard />} />
              <Route path='health' element={<HealthStatus />} />
            </Route>

            {/* Fallback Route */}
            <Route path='*' element={<Navigate to='/dashboard' replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </DBProvider>
  );
};

export default App;
