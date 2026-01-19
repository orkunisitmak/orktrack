import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Activity, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authAPI } from '@/lib/api'
import { cn } from '@/lib/utils'

export default function Login() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<{
    has_garmin_credentials: boolean
    has_gemini_key: boolean
    has_saved_tokens: boolean
  } | null>(null)

  const { login, isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  // Fetch config on mount
  useEffect(() => {
    authAPI.config().then(setConfig).catch(console.error)
    
    // If already authenticated, redirect to dashboard
    if (isAuthenticated) {
      // Verify with backend
      authAPI.status().then((status) => {
        if (status.authenticated) {
          navigate('/')
        }
      }).catch(() => {
        // Backend not reachable or session expired
      })
    }
  }, [isAuthenticated, navigate])

  const handleConnect = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await authAPI.login({ use_saved_tokens: true })

      if (result.success && result.user) {
        login(result.user)
        navigate('/')
      } else {
        setError(result.message || 'Failed to connect')
      }
    } catch (e: any) {
      setError(e.message || 'Failed to connect to Garmin')
    } finally {
      setIsLoading(false)
    }
  }

  const features = [
    { icon: '📊', title: 'Dashboard', desc: 'Visualize all your health metrics' },
    { icon: '💬', title: 'AI Chat', desc: 'Ask questions about your data' },
    { icon: '📅', title: 'Planner', desc: 'AI-generated workout plans' },
    { icon: '💡', title: 'Insights', desc: 'Personalized health insights' },
  ]

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-background to-purple-500/5" />
      
      {/* Animated circles */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.1, 0.2, 0.1],
          }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute -top-1/4 -right-1/4 w-[800px] h-[800px] rounded-full bg-primary/10 blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.1, 0.15, 0.1],
          }}
          transition={{ duration: 10, repeat: Infinity, delay: 1 }}
          className="absolute -bottom-1/4 -left-1/4 w-[600px] h-[600px] rounded-full bg-purple-500/10 blur-3xl"
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-lg"
      >
        {/* Card */}
        <div className="glass rounded-3xl p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', delay: 0.2 }}
              className="inline-flex p-4 rounded-2xl bg-primary/20 mb-4"
            >
              <Activity className="w-10 h-10 text-primary" />
            </motion.div>
            <h1 className="text-3xl font-bold gradient-text mb-2">OrkTrack</h1>
            <p className="text-muted-foreground">AI-Powered Garmin Fitness Dashboard</p>
          </div>

          {/* Features grid */}
          <div className="grid grid-cols-2 gap-4 mb-8">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="p-4 rounded-xl bg-muted/30 text-center"
              >
                <div className="text-2xl mb-2">{feature.icon}</div>
                <h3 className="font-semibold text-sm mb-1">{feature.title}</h3>
                <p className="text-xs text-muted-foreground">{feature.desc}</p>
              </motion.div>
            ))}
          </div>

          {/* Status indicators */}
          {config && (
            <div className="space-y-2 mb-6">
              <StatusItem
                ok={config.has_garmin_credentials}
                label="Garmin credentials"
              />
              <StatusItem
                ok={config.has_gemini_key}
                label="Gemini API key"
              />
              <StatusItem
                ok={config.has_saved_tokens}
                label="Saved session"
              />
            </div>
          )}

          {/* Error message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 p-4 rounded-xl bg-destructive/20 text-destructive mb-6"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </motion.div>
          )}

          {/* Connect button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleConnect}
            disabled={isLoading}
            className={cn(
              'w-full py-4 px-6 rounded-xl font-semibold text-lg',
              'bg-gradient-to-r from-primary to-purple-500',
              'text-white shadow-lg shadow-primary/30',
              'hover:shadow-xl hover:shadow-primary/40 transition-all',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center justify-center gap-3'
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Activity className="w-5 h-5" />
                Connect to Garmin
              </>
            )}
          </motion.button>

          {/* Help text */}
          <p className="text-center text-xs text-muted-foreground mt-4">
            Make sure you have configured your credentials in the .env file
          </p>
        </div>
      </motion.div>
    </div>
  )
}

function StatusItem({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {ok ? (
        <CheckCircle className="w-4 h-4 text-green-500" />
      ) : (
        <AlertCircle className="w-4 h-4 text-yellow-500" />
      )}
      <span className={ok ? 'text-green-500' : 'text-yellow-500'}>{label}</span>
    </div>
  )
}
