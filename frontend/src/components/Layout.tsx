import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  LayoutDashboard, 
  MessageSquare, 
  Calendar, 
  Lightbulb, 
  LogOut,
  Activity,
  X,
  Send,
  Loader2,
  Sparkles,
  User,
  Settings,
  ChevronUp,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { authAPI, aiAPI } from '@/lib/api'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/planner', icon: Calendar, label: 'Planner' },
  { to: '/insights', icon: Lightbulb, label: 'Insights' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [showChat, setShowChat] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)

  const handleLogout = async () => {
    try {
      await authAPI.logout()
    } catch (e) {
      // Ignore errors
    }
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Top Header - minimal */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="flex items-center justify-between px-4 py-3 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="p-1.5 rounded-lg bg-primary/20">
              <Activity className="w-5 h-5 text-primary" />
            </div>
            <h1 className="text-lg font-bold gradient-text">OrkTrack</h1>
          </div>
          
          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 hover:bg-muted transition-colors"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-purple-500 flex items-center justify-center text-white text-sm font-bold">
                {user?.displayName?.[0] || 'U'}
              </div>
              <ChevronUp className={cn(
                "w-4 h-4 text-muted-foreground transition-transform",
                showUserMenu && "rotate-180"
              )} />
            </button>
            
            <AnimatePresence>
              {showUserMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 top-full mt-2 w-48 rounded-xl bg-card border border-border shadow-xl overflow-hidden z-50"
                >
                  <div className="p-3 border-b border-border">
                    <p className="font-medium text-sm">{user?.displayName || 'User'}</p>
                    <p className="text-xs text-muted-foreground">Connected to Garmin</p>
                  </div>
                  <div className="p-1">
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-lg transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>

      {/* Floating Bottom Navigation */}
      <nav className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50">
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center gap-1 px-2 py-2 rounded-2xl bg-card/95 backdrop-blur-xl border border-border shadow-2xl shadow-black/20"
        >
          {navItems.map((item) => {
            const isActive = location.pathname === item.to || 
              (item.to !== '/' && location.pathname.startsWith(item.to))
            
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn(
                  'flex flex-col items-center gap-1 px-5 py-2 rounded-xl transition-all duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                )}
              >
                <item.icon className="w-5 h-5" />
                <span className="text-xs font-medium">{item.label}</span>
              </NavLink>
            )
          })}
          
          {/* Divider */}
          <div className="w-px h-10 bg-border mx-1" />
          
          {/* AI Chat Button */}
          <button
            onClick={() => setShowChat(true)}
            className={cn(
              'flex flex-col items-center gap-1 px-5 py-2 rounded-xl transition-all duration-200',
              'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
              'hover:shadow-lg hover:shadow-purple-500/30'
            )}
          >
            <MessageSquare className="w-5 h-5" />
            <span className="text-xs font-medium">AI Chat</span>
          </button>
        </motion.div>
      </nav>

      {/* AI Chat Popup */}
      <AnimatePresence>
        {showChat && (
          <AIChatPopup onClose={() => setShowChat(false)} />
        )}
      </AnimatePresence>
      
      {/* Click outside to close user menu */}
      {showUserMenu && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowUserMenu(false)} 
        />
      )}
    </div>
  )
}

// AI Chat Popup Component
function AIChatPopup({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    { role: 'assistant', content: "Hi! I'm your AI fitness coach. Ask me anything about your training, health metrics, or get personalized advice based on your Garmin data." }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    
    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)
    
    try {
      const response = await aiAPI.chat(userMessage)
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }])
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I couldn't process your request. Please try again." 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      {/* Chat Panel - No backdrop, floating in corner */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        className="fixed bottom-24 right-4 w-[380px] max-w-[calc(100vw-2rem)] h-[480px] max-h-[60vh] bg-card rounded-2xl border border-border shadow-2xl z-40 flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-gradient-to-r from-purple-500/10 to-pink-500/10">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold">AI Coach</h3>
              <p className="text-xs text-muted-foreground">Your personal fitness assistant</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted/50 transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn(
                'flex gap-2',
                msg.role === 'user' && 'flex-row-reverse'
              )}
            >
              <div className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0',
                msg.role === 'assistant' 
                  ? 'bg-gradient-to-r from-purple-500 to-pink-500'
                  : 'bg-primary'
              )}>
                {msg.role === 'assistant' 
                  ? <Sparkles className="w-4 h-4 text-white" />
                  : <User className="w-4 h-4 text-white" />
                }
              </div>
              <div className={cn(
                'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
                msg.role === 'assistant'
                  ? 'bg-muted/50 rounded-tl-sm'
                  : 'bg-primary text-primary-foreground rounded-tr-sm'
              )}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-muted/50 rounded-2xl rounded-tl-sm px-4 py-2">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
        </div>
        
        {/* Input */}
        <div className="p-4 border-t border-border">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about your training..."
              className="flex-1 px-4 py-2 rounded-xl bg-muted/50 border border-border focus:border-primary focus:outline-none text-sm"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="p-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-purple-500/30 transition-all"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>
    </>
  )
}

// Export for use in other components if needed
export { AIChatPopup }
