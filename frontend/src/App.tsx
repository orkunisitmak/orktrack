import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { authAPI } from '@/lib/api'
import Layout from '@/components/Layout'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Chat from '@/pages/Chat'
import Planner from '@/pages/Planner'
import Insights from '@/pages/Insights'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [isChecking, setIsChecking] = useState(true)
  const login = useAuthStore((state) => state.login)
  const logout = useAuthStore((state) => state.logout)

  useEffect(() => {
    // Check if backend has valid session
    const checkSession = async () => {
      try {
        const status = await authAPI.status()
        if (status.authenticated && status.user) {
          login(status.user)
        } else if (isAuthenticated) {
          // Frontend thinks we're authenticated but backend doesn't
          // Try to restore session with saved tokens
          try {
            const result = await authAPI.restore()
            if (result.success && result.user) {
              login(result.user)
            } else {
              logout()
            }
          } catch (e) {
            logout()
          }
        }
      } catch (e) {
        // If we can't reach the backend, stay on current page
        console.error('Session check failed:', e)
      }
      setIsChecking(false)
    }

    checkSession()
  }, [])

  if (isChecking) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Checking session...</p>
        </div>
      </div>
    )
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="chat" element={<Chat />} />
          <Route path="planner" element={<Planner />} />
          <Route path="insights" element={<Insights />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
