import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Activities from './pages/Activities'
import Trends from './pages/Trends'
import RouteMap from './pages/RouteMap'
import RouteCompare from './pages/RouteCompare'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Layout from './components/Layout'
import { getAccessToken } from './api/client'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = getAccessToken()
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/activities" element={<Activities />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/routes" element={<RouteMap />} />
        <Route path="/routes/:id/compare" element={<RouteCompare />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
