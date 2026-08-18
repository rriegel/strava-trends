import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Activities from './pages/Activities'
import Trends from './pages/Trends'
import RouteMap from './pages/RouteMap'
import Login from './pages/Login'
import StravaCallback from './pages/StravaCallback'
import Layout from './components/Layout'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/strava/callback" element={<StravaCallback />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/activities" element={<Activities />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/routes" element={<RouteMap />} />
      </Route>
    </Routes>
  )
}

export default App
