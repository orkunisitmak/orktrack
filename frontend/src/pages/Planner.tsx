import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Calendar,
  Loader2,
  Play,
  Zap,
  AlertTriangle,
  CheckCircle,
  Brain,
  TrendingUp,
  Heart,
  Moon,
  Activity,
  Clock,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Sparkles,
  RefreshCw,
  Pin,
  CalendarDays,
  ListChecks,
  Target,
  Timer,
  Send,
  Check,
  X,
  Plus,
  Trash2,
  LayoutGrid,
  List,
  Dumbbell,
} from 'lucide-react'
import { aiAPI, healthAPI, activitiesAPI, workoutsAPI } from '@/lib/api'
import { cn, formatDuration } from '@/lib/utils'

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_ABBREV = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const GOALS = [
  { id: 'general', name: 'General Fitness', icon: '💪', desc: 'Balanced training', hasTime: false },
  { id: '5k', name: '5K Race', icon: '🏃', desc: 'Speed focus', hasTime: true, distance: 5, placeholder: '25:00', examples: ['18:00', '20:00', '22:00', '25:00', '30:00'] },
  { id: '10k', name: '10K Race', icon: '🏃‍♂️', desc: 'Speed endurance', hasTime: true, distance: 10, placeholder: '50:00', examples: ['38:00', '42:00', '45:00', '50:00', '55:00'] },
  { id: 'half', name: 'Half Marathon', icon: '🏅', desc: 'Endurance', hasTime: true, distance: 21.0975, placeholder: '1:45:00', examples: ['1:25:00', '1:30:00', '1:45:00', '2:00:00'] },
  { id: 'full', name: 'Marathon', icon: '🏆', desc: 'Long distance', hasTime: true, distance: 42.195, placeholder: '3:45:00', examples: ['2:59:00', '3:15:00', '3:30:00', '4:00:00'] },
  { id: 'weight_loss', name: 'Weight Loss', icon: '⚖️', desc: 'Calorie burn', hasTime: false },
]

const SUPPLEMENTARY_ACTIVITIES = [
  { id: 'wim_hof', name: 'Wim Hof Breathing', icon: '🧘‍♂️', duration: '15-20 min' },
  { id: 'mobility', name: 'Mobility Work', icon: '🔄', duration: '10-15 min' },
  { id: 'yoga', name: 'Yoga / Stretching', icon: '🧘', duration: '30-60 min' },
  { id: 'cold_plunge', name: 'Cold Plunge', icon: '❄️', duration: '2-5 min' },
  { id: 'gym', name: 'Gym / Strength', icon: '🏋️', duration: '45-60 min' },
]

// Convert time string to seconds
const parseTimeToSeconds = (time: string): number => {
  const parts = time.split(':').map(Number)
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  return 0
}

const formatSecondsToTime = (seconds: number): string => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

const calculateVDOT = (distanceKm: number, timeSeconds: number): number => {
  const paceMinPerKm = (timeSeconds / 60) / distanceKm
  if (paceMinPerKm < 3.0) return 80
  if (paceMinPerKm < 3.2) return 75
  if (paceMinPerKm < 3.4) return 70
  if (paceMinPerKm < 3.6) return 65
  if (paceMinPerKm < 4.0) return 60
  if (paceMinPerKm < 4.3) return 55
  if (paceMinPerKm < 4.7) return 50
  if (paceMinPerKm < 5.2) return 45
  if (paceMinPerKm < 5.7) return 40
  if (paceMinPerKm < 6.3) return 35
  return 30
}

const getWorkoutTypeColor = (type: string) => {
  const t = type?.toLowerCase() || ''
  if (t.includes('rest')) return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  if (t.includes('easy') || t.includes('recovery')) return 'bg-green-500/20 text-green-400 border-green-500/30'
  if (t.includes('tempo') || t.includes('threshold')) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
  if (t.includes('interval') || t.includes('vo2') || t.includes('speed')) return 'bg-red-500/20 text-red-400 border-red-500/30'
  if (t.includes('long')) return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
  if (t.includes('strength') || t.includes('gym')) return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
  return 'bg-primary/20 text-primary border-primary/30'
}

const getIntensityDot = (intensity: string) => {
  switch (intensity?.toLowerCase()) {
    case 'low': return 'bg-green-500'
    case 'moderate': return 'bg-yellow-500'
    case 'high': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

export default function Planner() {
  const queryClient = useQueryClient()
  
  // UI State
  const [showPlanGenerator, setShowPlanGenerator] = useState(false)
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list')
  const [expandedWorkout, setExpandedWorkout] = useState<string | null>(null)
  
  // Generation State
  const [selectedGoal, setSelectedGoal] = useState(GOALS[0])
  const [goalTime, setGoalTime] = useState<string>('')
  const [planType, setPlanType] = useState<'week' | 'month'>('week')
  const [generatedPlan, setGeneratedPlan] = useState<any>(null)
  const [supplementaryFrequency, setSupplementaryFrequency] = useState<Record<string, number>>({})

  // Queries
  const { data: todayReadiness } = useQuery({
    queryKey: ['today-readiness'],
    queryFn: () => aiAPI.getTodayReadiness(),
  })

  const { data: pinnedPlans, refetch: refetchPinnedPlans } = useQuery({
    queryKey: ['pinned-plans'],
    queryFn: () => aiAPI.getPinnedPlans(),
  })

  const activePlan = pinnedPlans?.plans?.[0] // Get first (most recent) pinned plan
  
  const { data: activePlanDetails, isLoading: loadingDetails } = useQuery({
    queryKey: ['pinned-plan-details', activePlan?.id],
    queryFn: () => activePlan?.id ? aiAPI.getPinnedPlanDetails(activePlan.id) : null,
    enabled: !!activePlan?.id,
  })

  // Mutations
  const selectedSupplementary = Object.entries(supplementaryFrequency)
    .filter(([_, freq]) => freq > 0)
    .map(([id]) => id)

  const goalVDOT = selectedGoal.hasTime && goalTime && selectedGoal.distance
    ? calculateVDOT(selectedGoal.distance, parseTimeToSeconds(goalTime))
    : null

  const getGoalString = () => {
    if (selectedGoal.hasTime && goalTime) return `${selectedGoal.name} in ${goalTime}`
    return selectedGoal.name
  }

  const generateMutation = useMutation({
    mutationFn: () => planType === 'week'
      ? aiAPI.generateWeekPlan({
          primary_goal: getGoalString(),
          supplementary_activities: selectedSupplementary,
          supplementary_frequency: supplementaryFrequency,
          goal_time: selectedGoal.hasTime ? goalTime : undefined,
          goal_distance_km: selectedGoal.hasTime ? selectedGoal.distance : undefined,
          target_vdot: goalVDOT || undefined,
        })
      : aiAPI.generateMonthPlan({
          primary_goal: getGoalString(),
          training_phase: 'Build Phase',
          supplementary_activities: selectedSupplementary,
          supplementary_frequency: supplementaryFrequency,
          goal_time: selectedGoal.hasTime ? goalTime : undefined,
          goal_distance_km: selectedGoal.hasTime ? selectedGoal.distance : undefined,
          target_vdot: goalVDOT || undefined,
        }),
    onSuccess: (data) => setGeneratedPlan(data),
  })

  const pinMutation = useMutation({
    mutationFn: () => aiAPI.pinPlan({ plan_type: planType, plan_data: generatedPlan }),
    onSuccess: () => {
      refetchPinnedPlans()
      setGeneratedPlan(null)
      setShowPlanGenerator(false)
    },
  })

  const deletePlanMutation = useMutation({
    mutationFn: (planId: number) => aiAPI.deletePinnedPlan(planId),
    onSuccess: () => refetchPinnedPlans(),
  })

  const toggleSupplementary = (id: string) => {
    setSupplementaryFrequency(prev => {
      if (prev[id] && prev[id] > 0) {
        const { [id]: _, ...rest } = prev
        return rest
      }
      return { ...prev, [id]: 7 }
    })
  }

  const hasPinnedPlan = !!activePlan

  // Calendar data processing
  const calendarData = useMemo(() => {
    if (!activePlanDetails?.workouts) return []
    
    const workouts = activePlanDetails.workouts
    const startDate = new Date(activePlan?.start_date || new Date())
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    
    // Group workouts by week
    const weeks: any[][] = []
    let currentWeek: any[] = []
    
    // Find the Monday of the start week
    const firstMonday = new Date(startDate)
    while (firstMonday.getDay() !== 1) {
      firstMonday.setDate(firstMonday.getDate() - 1)
    }
    
    workouts.forEach((workout: any, idx: number) => {
      const workoutDate = new Date(workout.scheduled_date)
      currentWeek.push({
        ...workout,
        date: workoutDate,
        isToday: workoutDate.toDateString() === today.toDateString(),
        isPast: workoutDate < today,
      })
      
      if (currentWeek.length === 7 || idx === workouts.length - 1) {
        weeks.push([...currentWeek])
        currentWeek = []
      }
    })
    
    return weeks
  }, [activePlanDetails, activePlan])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Training Planner</h1>
          <p className="text-sm text-muted-foreground">
            {hasPinnedPlan ? 'Your active training plan' : 'Create your personalized training plan'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {hasPinnedPlan && (
            <div className="flex items-center bg-muted rounded-lg p-1">
              <button
                onClick={() => setViewMode('list')}
                className={cn(
                  'p-2 rounded-md transition-colors',
                  viewMode === 'list' ? 'bg-card shadow-sm' : 'hover:bg-card/50'
                )}
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('calendar')}
                className={cn(
                  'p-2 rounded-md transition-colors',
                  viewMode === 'calendar' ? 'bg-card shadow-sm' : 'hover:bg-card/50'
                )}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
            </div>
          )}
          
          <button
            onClick={() => setShowPlanGenerator(!showPlanGenerator)}
            className={cn(
              'px-4 py-2 rounded-xl flex items-center gap-2 transition-all',
              showPlanGenerator 
                ? 'bg-primary text-white' 
                : 'bg-muted hover:bg-muted/80'
            )}
          >
            {showPlanGenerator ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showPlanGenerator ? 'Close' : 'New Plan'}
          </button>
        </div>
      </div>

      {/* Today's Readiness Alert */}
      {todayReadiness && (todayReadiness.should_rest || todayReadiness.should_reduce_intensity) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            'p-4 rounded-xl border flex items-start gap-3',
            todayReadiness.should_rest
              ? 'bg-red-500/10 border-red-500/30'
              : 'bg-yellow-500/10 border-yellow-500/30'
          )}
        >
          <AlertTriangle className={cn(
            'w-5 h-5 mt-0.5',
            todayReadiness.should_rest ? 'text-red-500' : 'text-yellow-500'
          )} />
          <div className="flex-1">
            <p className={cn(
              'font-semibold text-sm',
              todayReadiness.should_rest ? 'text-red-500' : 'text-yellow-500'
            )}>
              {todayReadiness.should_rest ? 'Rest Day Recommended' : 'Reduce Intensity Today'}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">{todayReadiness.adjustment_reason}</p>
          </div>
        </motion.div>
      )}

      {/* Plan Generator Panel */}
      <AnimatePresence>
        {showPlanGenerator && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="p-6 rounded-2xl bg-card border border-border space-y-6">
              {/* Generated Plan Preview */}
              {generatedPlan ? (
                <GeneratedPlanPreview
                  plan={generatedPlan}
                  planType={planType}
                  onPin={() => pinMutation.mutate()}
                  onRegenerate={() => generateMutation.mutate()}
                  onDiscard={() => setGeneratedPlan(null)}
                  isPinning={pinMutation.isPending}
                  isRegenerating={generateMutation.isPending}
                />
              ) : (
                <>
                  {/* Goal Selection */}
                  <div>
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4 text-primary" />
                      Your Goal
                    </h3>
                    <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                      {GOALS.map((goal) => (
                        <button
                          key={goal.id}
                          onClick={() => {
                            setSelectedGoal(goal)
                            setGoalTime('')
                          }}
                          className={cn(
                            'p-3 rounded-xl border transition-all text-center',
                            selectedGoal.id === goal.id
                              ? 'bg-primary/10 border-primary'
                              : 'border-border hover:border-primary/50'
                          )}
                        >
                          <span className="text-2xl">{goal.icon}</span>
                          <p className="text-xs font-medium mt-1">{goal.name}</p>
                        </button>
                      ))}
                    </div>
                    
                    {selectedGoal.hasTime && (
                      <div className="mt-4">
                        <label className="text-xs text-muted-foreground mb-1 block">Target Time</label>
                        <input
                          type="text"
                          value={goalTime}
                          onChange={(e) => setGoalTime(e.target.value)}
                          placeholder={selectedGoal.placeholder}
                          className="w-full px-4 py-2 rounded-lg bg-muted border border-border focus:border-primary focus:outline-none"
                        />
                        <div className="flex gap-2 mt-2 flex-wrap">
                          {selectedGoal.examples?.map((ex) => (
                            <button
                              key={ex}
                              onClick={() => setGoalTime(ex)}
                              className="px-2 py-1 text-xs rounded bg-muted hover:bg-muted/80"
                            >
                              {ex}
                            </button>
                          ))}
                        </div>
                        {goalVDOT && (
                          <p className="text-xs text-primary mt-2">
                            Estimated VDOT: {goalVDOT} | Target pace: {formatSecondsToTime(parseTimeToSeconds(goalTime) / selectedGoal.distance!)}/km
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Supplementary Activities */}
                  <div>
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Dumbbell className="w-4 h-4 text-primary" />
                      Add to Plan (Optional)
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                      {SUPPLEMENTARY_ACTIVITIES.map((act) => {
                        const isSelected = supplementaryFrequency[act.id] > 0
                        return (
                          <div
                            key={act.id}
                            className={cn(
                              'p-3 rounded-xl border transition-all',
                              isSelected
                                ? 'bg-primary/10 border-primary'
                                : 'border-border hover:border-primary/50'
                            )}
                          >
                            <button
                              onClick={() => toggleSupplementary(act.id)}
                              className="w-full flex items-center gap-2"
                            >
                              <div className={cn(
                                'w-5 h-5 rounded border flex items-center justify-center text-xs',
                                isSelected ? 'bg-primary border-primary text-white' : 'border-border'
                              )}>
                                {isSelected && <Check className="w-3 h-3" />}
                              </div>
                              <span className="text-lg">{act.icon}</span>
                              <span className="text-xs font-medium truncate">{act.name}</span>
                            </button>
                            {isSelected && (
                              <div className="flex items-center justify-center gap-1 mt-2">
                                <button
                                  onClick={() => setSupplementaryFrequency(p => ({ ...p, [act.id]: Math.max(1, (p[act.id] || 7) - 1) }))}
                                  className="w-6 h-6 rounded bg-muted flex items-center justify-center text-xs"
                                >
                                  -
                                </button>
                                <span className="text-xs font-medium w-8 text-center text-primary">
                                  {supplementaryFrequency[act.id]}x
                                </span>
                                <button
                                  onClick={() => setSupplementaryFrequency(p => ({ ...p, [act.id]: Math.min(7, (p[act.id] || 7) + 1) }))}
                                  className="w-6 h-6 rounded bg-muted flex items-center justify-center text-xs"
                                >
                                  +
                                </button>
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Generate Buttons */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        setPlanType('week')
                        generateMutation.mutate()
                      }}
                      disabled={generateMutation.isPending}
                      className="flex-1 py-3 rounded-xl bg-gradient-to-r from-primary to-purple-500 text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {generateMutation.isPending && planType === 'week' ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Calendar className="w-5 h-5" />
                      )}
                      Generate Week Plan
                    </button>
                    <button
                      onClick={() => {
                        setPlanType('month')
                        generateMutation.mutate()
                      }}
                      disabled={generateMutation.isPending}
                      className="flex-1 py-3 rounded-xl bg-gradient-to-r from-orange-500 to-red-500 text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      {generateMutation.isPending && planType === 'month' ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <CalendarDays className="w-5 h-5" />
                      )}
                      Generate Month Plan
                    </button>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Active Plan Display */}
      {hasPinnedPlan && activePlanDetails ? (
        <div className="space-y-4">
          {/* Plan Header */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/20">
                <Pin className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="font-semibold">{activePlan.plan_name}</h3>
                <p className="text-xs text-muted-foreground">
                  {activePlan.plan_type === 'week' ? '7-Day Plan' : '4-Week Plan'} • 
                  {new Date(activePlan.start_date).toLocaleDateString()} - {new Date(activePlan.end_date).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="text-right mr-4">
                <p className="text-2xl font-bold text-primary">{activePlan.progress}%</p>
                <p className="text-xs text-muted-foreground">{activePlan.completed_workouts}/{activePlan.total_workouts} workouts</p>
              </div>
              <button
                onClick={() => {
                  if (confirm('Delete this plan?')) deletePlanMutation.mutate(activePlan.id)
                }}
                className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* View Modes */}
          {viewMode === 'calendar' ? (
            <CalendarView weeks={calendarData} expandedWorkout={expandedWorkout} setExpandedWorkout={setExpandedWorkout} />
          ) : (
            <ListView workouts={activePlanDetails.workouts} expandedWorkout={expandedWorkout} setExpandedWorkout={setExpandedWorkout} />
          )}
        </div>
      ) : loadingDetails ? (
        <div className="p-8 rounded-2xl bg-card border border-border flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : !showPlanGenerator ? (
        <div className="p-12 rounded-2xl bg-card border border-dashed border-border flex flex-col items-center justify-center text-center">
          <Calendar className="w-16 h-16 text-muted-foreground mb-4" />
          <h3 className="text-xl font-semibold mb-2">No Active Plan</h3>
          <p className="text-muted-foreground text-sm mb-6 max-w-md">
            Create a personalized training plan based on your health data and goals. The AI will generate workouts with specific paces from your VDOT score.
          </p>
          <button
            onClick={() => setShowPlanGenerator(true)}
            className="px-6 py-3 rounded-xl bg-primary text-white font-semibold flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Create Your First Plan
          </button>
        </div>
      ) : null}
    </div>
  )
}

// Send to Garmin Section Component
function SendToGarminSection({ plan, planType }: { plan: any, planType: 'week' | 'month' }) {
  const [sendingWorkout, setSendingWorkout] = useState<string | null>(null)
  const [sentWorkouts, setSentWorkouts] = useState<Set<string>>(new Set())
  const [sendingAll, setSendingAll] = useState(false)

  // Extract workouts
  let workouts: any[] = []
  if (planType === 'week') {
    workouts = plan.workouts || []
  } else if (plan.weeks && Array.isArray(plan.weeks)) {
    workouts = plan.weeks.flatMap((w: any) => w.workouts || [])
  }

  const handleSendWorkout = async (workout: any, idx: number) => {
    const workoutId = `workout-${idx}`
    setSendingWorkout(workoutId)
    try {
      // Map workout steps to the format expected by backend
      const formattedSteps = (workout.steps || []).map((step: any) => ({
        type: step.type || 'active',
        duration_minutes: step.duration_minutes || null,
        distance_meters: step.distance_meters || null,
        target_type: step.target_pace_min ? 'pace' : 'open',
        target_pace_min: step.target_pace_min || null,
        target_pace_max: step.target_pace_max || null,
        description: step.description || '',
      }))
      
      await workoutsAPI.sendToGarmin({
        title: workout.title || `Day ${idx + 1}`,
        type: workout.type || 'running',
        duration_minutes: workout.duration_minutes || 30,
        steps: formattedSteps,
        description: workout.description || workout.title || 'Training workout',
      })
      setSentWorkouts(prev => new Set(prev).add(workoutId))
    } catch (err) {
      console.error('Failed to send workout:', err)
    } finally {
      setSendingWorkout(null)
    }
  }

  const handleSendAll = async () => {
    setSendingAll(true)
    for (let i = 0; i < workouts.length; i++) {
      const workout = workouts[i]
      if (workout.type === 'rest') continue
      await handleSendWorkout(workout, i)
    }
    setSendingAll(false)
  }

  const runnableWorkouts = workouts.filter((w: any) => w.type !== 'rest')

  if (runnableWorkouts.length === 0) return null

  return (
    <div className="p-4 rounded-xl bg-muted/30 border border-border space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Send className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Send to Garmin</span>
        </div>
        <button
          onClick={handleSendAll}
          disabled={sendingAll}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2',
            'bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors',
            sendingAll && 'opacity-50'
          )}
        >
          {sendingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          Send All Workouts
        </button>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {workouts.map((workout: any, idx: number) => {
          const workoutId = `workout-${idx}`
          const isSent = sentWorkouts.has(workoutId)
          const isSending = sendingWorkout === workoutId
          const isRest = workout.type === 'rest'
          
          if (isRest) return null
          
          return (
            <button
              key={workoutId}
              onClick={() => handleSendWorkout(workout, idx)}
              disabled={isSending || isSent}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all',
                isSent 
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-card border border-border hover:bg-muted'
              )}
            >
              {isSending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : isSent ? (
                <Check className="w-3 h-3" />
              ) : (
                <Send className="w-3 h-3" />
              )}
              Day {idx + 1}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Generated Plan Preview Component
function GeneratedPlanPreview({
  plan,
  planType,
  onPin,
  onRegenerate,
  onDiscard,
  isPinning,
  isRegenerating,
}: {
  plan: any
  planType: 'week' | 'month'
  onPin: () => void
  onRegenerate: () => void
  onDiscard: () => void
  isPinning: boolean
  isRegenerating: boolean
}) {
  const [expandedWorkout, setExpandedWorkout] = useState<string | null>(null)
  
  // Extract workouts from different possible structures
  let workouts: any[] = []
  
  if (planType === 'week') {
    workouts = plan.workouts || []
  } else {
    // Month plan - try weeks array first
    if (plan.weeks && Array.isArray(plan.weeks)) {
      workouts = plan.weeks.flatMap((w: any) => w.workouts || [])
    } else if (plan.workouts && Array.isArray(plan.workouts)) {
      // Fallback: workouts at root level
      workouts = plan.workouts
    }
  }

  const toggleWorkout = (id: string) => {
    setExpandedWorkout(expandedWorkout === id ? null : id)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            Generated Plan
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {plan.plan_name || `${planType === 'week' ? '7-Day' : '4-Week'} Training Plan`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onDiscard}
            className="px-3 py-1.5 rounded-lg text-sm border border-border hover:bg-muted transition-colors"
          >
            Discard
          </button>
          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="px-3 py-1.5 rounded-lg text-sm border border-border hover:bg-muted flex items-center gap-1 transition-colors"
          >
            <RefreshCw className={cn('w-3 h-3', isRegenerating && 'animate-spin')} />
            Regenerate
          </button>
          <button
            onClick={onPin}
            disabled={isPinning}
            className="px-4 py-1.5 rounded-lg text-sm bg-primary text-white flex items-center gap-1"
          >
            {isPinning ? <Loader2 className="w-3 h-3 animate-spin" /> : <Pin className="w-3 h-3" />}
            Save Plan
          </button>
        </div>
      </div>

      {/* Send to Garmin Section */}
      <SendToGarminSection plan={plan} planType={planType} />

      {(plan.rationale || plan.mesocycle_overview) && (
        <p className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
          {plan.rationale || plan.mesocycle_overview}
        </p>
      )}

      {/* Show weeks for month plan */}
      {planType === 'month' && plan.weeks && plan.weeks.length > 0 ? (
        <div className="space-y-6">
          {plan.weeks.slice(0, 4).map((week: any, weekIdx: number) => (
            <div key={weekIdx} className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">
                  Week {week.week_number || weekIdx + 1}
                </span>
                <span className="text-xs text-muted-foreground">
                  {week.week_focus || 'Training Week'}
                </span>
              </div>
              <div className="space-y-2">
                {(week.workouts || []).map((workout: any, idx: number) => {
                  const workoutId = `week-${weekIdx}-day-${idx}`
                  const isExpanded = expandedWorkout === workoutId
                  return (
                    <WorkoutCard
                      key={workoutId}
                      workout={workout}
                      dayIndex={idx}
                      isExpanded={isExpanded}
                      onToggle={() => toggleWorkout(workoutId)}
                    />
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {workouts.map((workout: any, idx: number) => {
            const workoutId = `day-${idx}`
            const isExpanded = expandedWorkout === workoutId
            return (
              <WorkoutCard
                key={workoutId}
                workout={workout}
                dayIndex={idx}
                isExpanded={isExpanded}
                onToggle={() => toggleWorkout(workoutId)}
              />
            )
          })}
        </div>
      )}
      
      {/* Show empty state if no workouts */}
      {workouts.length === 0 && (!plan.weeks || plan.weeks.length === 0) && (
        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 text-sm">
          <p>Plan generated but no workouts found. Try regenerating.</p>
          {plan.error && <p className="mt-1 opacity-70">Error: {plan.error}</p>}
        </div>
      )}

      {/* Summary stats */}
      {(() => {
        // Calculate summary from available data
        let totalWorkouts = 0
        let totalDuration = 0
        let totalDistance = 0
        let restDays = 0
        
        if (plan.weekly_summary) {
          totalWorkouts = plan.weekly_summary.total_workouts || 0
          totalDuration = plan.weekly_summary.total_duration_hours || 0
          totalDistance = plan.weekly_summary.estimated_distance_km || 0
          restDays = plan.weekly_summary.rest_days || 0
        } else if (plan.weeks && Array.isArray(plan.weeks)) {
          // Calculate from weeks for month plan
          plan.weeks.forEach((week: any) => {
            totalWorkouts += week.total_workouts || week.workouts?.length || 0
            totalDuration += week.total_duration_hours || 0
            totalDistance += week.total_distance_km || 0
            if (week.workouts) {
              restDays += week.workouts.filter((w: any) => w.type === 'rest').length
            }
          })
        } else if (workouts.length > 0) {
          // Calculate from workouts array
          totalWorkouts = workouts.length
          totalDuration = workouts.reduce((acc: number, w: any) => acc + (w.duration_minutes || 0), 0) / 60
          totalDistance = workouts.reduce((acc: number, w: any) => acc + (w.estimated_distance_km || 0), 0)
          restDays = workouts.filter((w: any) => w.type === 'rest').length
        }
        
        if (totalWorkouts === 0 && totalDuration === 0) return null
        
        return (
          <div className="grid grid-cols-4 gap-4 p-4 rounded-lg bg-muted/50">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">{totalWorkouts}</p>
              <p className="text-xs text-muted-foreground">Workouts</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{totalDuration.toFixed(1)}h</p>
              <p className="text-xs text-muted-foreground">Duration</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{totalDistance.toFixed(0)}km</p>
              <p className="text-xs text-muted-foreground">Distance</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{restDays}</p>
              <p className="text-xs text-muted-foreground">Rest Days</p>
            </div>
          </div>
        )
      })()}
    </div>
  )
}

// Expandable Workout Card for Generated Plan Preview
function WorkoutCard({
  workout,
  dayIndex,
  isExpanded,
  onToggle,
}: {
  workout: any
  dayIndex: number
  isExpanded: boolean
  onToggle: () => void
}) {
  const dayName = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dayIndex] || workout.day
  
  return (
    <div className={cn(
      'rounded-xl border overflow-hidden transition-all',
      getWorkoutTypeColor(workout.type)
    )}>
      {/* Header - always visible */}
      <button
        onClick={onToggle}
        className="w-full p-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="text-left">
            <p className="text-xs font-medium opacity-70">{dayName}</p>
            <p className="font-semibold">{workout.title || workout.type}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right text-sm">
            <span className="opacity-70">{workout.duration_minutes}m</span>
            {workout.estimated_distance_km > 0 && (
              <span className="ml-2 opacity-70">{workout.estimated_distance_km.toFixed(1)}km</span>
            )}
          </div>
          <ChevronDown className={cn(
            'w-4 h-4 transition-transform',
            isExpanded && 'rotate-180'
          )} />
        </div>
      </button>
      
      {/* Expanded details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-3 border-t border-white/10 pt-3">
              {/* Description */}
              {workout.description && (
                <p className="text-sm opacity-80">{workout.description}</p>
              )}
              
              {/* Key Focus */}
              {workout.key_focus && (
                <div className="text-sm">
                  <span className="font-medium">Key Focus: </span>
                  <span className="opacity-80">{workout.key_focus}</span>
                </div>
              )}
              
              {/* Target HR Zone */}
              {workout.target_hr_zone && (
                <div className="text-sm">
                  <span className="font-medium">Target HR: </span>
                  <span className="opacity-80">{workout.target_hr_zone}</span>
                </div>
              )}
              
              {/* Workout Steps */}
              {workout.steps && workout.steps.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-semibold opacity-70 uppercase tracking-wide">Workout Steps</p>
                  <div className="space-y-1">
                    {workout.steps.map((step: any, idx: number) => {
                      // Build duration/distance string - prioritize distance_meters for track work
                      const metrics: string[] = []
                      if (step.distance_meters) {
                        metrics.push(step.distance_meters >= 1000 
                          ? `${(step.distance_meters / 1000).toFixed(1)}km` 
                          : `${step.distance_meters}m`)
                      } else if (step.distance_km) {
                        metrics.push(`${step.distance_km}km`)
                      } else if (step.duration_minutes) {
                        metrics.push(`${step.duration_minutes} min`)
                      } else if (step.duration) {
                        metrics.push(step.duration)
                      } else if (step.distance) {
                        metrics.push(step.distance)
                      }
                      
                      // Build pace string
                      const paceStr = step.target_pace_min && step.target_pace_max 
                        ? `${step.target_pace_min}-${step.target_pace_max}/km`
                        : step.target_pace 
                          ? `@ ${step.target_pace}`
                          : ''
                      
                      return (
                        <div
                          key={idx}
                          className={cn(
                            'text-xs px-3 py-2 rounded-lg flex items-center justify-between',
                            step.type === 'warmup' && 'bg-blue-500/20 border-l-2 border-blue-500',
                            step.type === 'cooldown' && 'bg-purple-500/20 border-l-2 border-purple-500',
                            step.type === 'work' && 'bg-red-500/20 border-l-2 border-red-500',
                            step.type === 'recovery' && 'bg-green-500/20 border-l-2 border-green-500',
                            !['warmup', 'cooldown', 'work', 'recovery'].includes(step.type) && 'bg-white/10 border-l-2 border-white/30'
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-semibold capitalize">{step.type}</span>
                            <span className="opacity-80">{step.description}</span>
                          </div>
                          <div className="flex items-center gap-3 font-medium">
                            {metrics.length > 0 && (
                              <span className="px-2 py-0.5 rounded bg-white/10">
                                {metrics.join(' ')}
                              </span>
                            )}
                            {paceStr && (
                              <span className="opacity-70">
                                {paceStr}
                              </span>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              
              {/* Supplementary Activities */}
              {workout.supplementary && workout.supplementary.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-orange-400 uppercase tracking-wide">+ Supplementary Activities</p>
                  <div className="space-y-2">
                    {workout.supplementary.map((supp: any, idx: number) => {
                      const activityName = supp.activity?.toLowerCase() || supp.type?.toLowerCase() || ''
                      const icon = activityName.includes('wim') || activityName.includes('breath') ? '🧘‍♂️' :
                                   activityName.includes('mobility') ? '🔄' :
                                   activityName.includes('yoga') || activityName.includes('stretch') ? '🧘' :
                                   activityName.includes('cold') || activityName.includes('plunge') ? '❄️' :
                                   activityName.includes('gym') || activityName.includes('strength') ? '🏋️' :
                                   activityName.includes('sauna') ? '🔥' : '✨'
                      const displayName = supp.activity || supp.type || 'Activity'
                      
                      return (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-slate-800/50 border border-slate-700/50"
                        >
                          <div className="flex items-start gap-3">
                            <span className="text-xl">{icon}</span>
                            <div className="flex-1">
                              <p className="font-semibold text-sm">{displayName}</p>
                              <p className="text-xs text-muted-foreground flex items-center gap-2">
                                <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
                                  {supp.timing || 'Flexible'}
                                </span>
                                <span>• {supp.duration_minutes || supp.duration || '15'} min</span>
                              </p>
                              {supp.notes && (
                                <p className="text-xs text-orange-300/80 mt-1">{supp.notes}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Calendar View Component
function CalendarView({
  weeks,
  expandedWorkout,
  setExpandedWorkout,
}: {
  weeks: any[][]
  expandedWorkout: string | null
  setExpandedWorkout: (id: string | null) => void
}) {
  return (
    <div className="space-y-2">
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-2">
        {DAY_ABBREV.map((day) => (
          <div key={day} className="text-center text-xs font-semibold text-muted-foreground py-2">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar weeks */}
      {weeks.map((week, weekIdx) => (
        <div key={weekIdx} className="grid grid-cols-7 gap-2">
          {week.map((workout: any, dayIdx: number) => (
            <motion.div
              key={`${weekIdx}-${dayIdx}`}
              whileHover={{ scale: 1.02 }}
              onClick={() => setExpandedWorkout(expandedWorkout === workout.id?.toString() ? null : workout.id?.toString())}
              className={cn(
                'p-2 rounded-lg border cursor-pointer transition-all min-h-[100px]',
                workout.isToday && 'ring-2 ring-primary',
                workout.isPast && workout.completed ? 'bg-green-500/10 border-green-500/30' : '',
                workout.isPast && !workout.completed ? 'opacity-50' : '',
                getWorkoutTypeColor(workout.workout_type)
              )}
            >
              <p className="text-xs font-medium opacity-70">
                {new Date(workout.scheduled_date).getDate()}
              </p>
              <p className="text-sm font-semibold mt-1 line-clamp-2">{workout.title}</p>
              <div className="flex items-center gap-1 mt-1">
                <Clock className="w-3 h-3 opacity-70" />
                <span className="text-xs opacity-70">{workout.duration_minutes}m</span>
              </div>
              {workout.completed && (
                <CheckCircle className="w-4 h-4 text-green-500 mt-1" />
              )}
            </motion.div>
          ))}
        </div>
      ))}
    </div>
  )
}

// List View Component
function ListView({
  workouts,
  expandedWorkout,
  setExpandedWorkout,
}: {
  workouts: any[]
  expandedWorkout: string | null
  setExpandedWorkout: (id: string | null) => void
}) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  // Group by week
  const grouped = workouts.reduce((acc: any, workout: any, idx: number) => {
    const weekNum = Math.floor(idx / 7)
    if (!acc[weekNum]) acc[weekNum] = []
    acc[weekNum].push(workout)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([weekNum, weekWorkouts]: [string, any]) => (
        <div key={weekNum} className="space-y-2">
          <h4 className="text-sm font-semibold text-muted-foreground">Week {parseInt(weekNum) + 1}</h4>
          <div className="space-y-2">
            {weekWorkouts.map((workout: any) => {
              const workoutDate = new Date(workout.scheduled_date)
              const isToday = workoutDate.toDateString() === today.toDateString()
              const isPast = workoutDate < today
              const isExpanded = expandedWorkout === workout.id?.toString()

              return (
                <motion.div
                  key={workout.id}
                  layout
                  className={cn(
                    'rounded-xl border overflow-hidden',
                    isToday && 'ring-2 ring-primary',
                    isPast && workout.completed ? 'bg-green-500/5 border-green-500/30' : 'bg-card border-border'
                  )}
                >
                  <button
                    onClick={() => setExpandedWorkout(isExpanded ? null : workout.id?.toString())}
                    className="w-full p-4 flex items-center justify-between text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'w-12 h-12 rounded-lg flex flex-col items-center justify-center',
                        isToday ? 'bg-primary text-white' : 'bg-muted'
                      )}>
                        <span className="text-xs opacity-70">{DAY_ABBREV[workoutDate.getDay() === 0 ? 6 : workoutDate.getDay() - 1]}</span>
                        <span className="text-lg font-bold">{workoutDate.getDate()}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold">{workout.title}</h4>
                          <span className={cn(
                            'px-2 py-0.5 rounded text-xs font-medium',
                            getWorkoutTypeColor(workout.workout_type)
                          )}>
                            {workout.workout_type}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {workout.duration_minutes} min
                          {workout.estimated_distance_km > 0 && ` • ${workout.estimated_distance_km.toFixed(1)} km`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {workout.completed && <CheckCircle className="w-5 h-5 text-green-500" />}
                      <ChevronDown className={cn(
                        'w-5 h-5 transition-transform',
                        isExpanded && 'rotate-180'
                      )} />
                    </div>
                  </button>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
                          {workout.description && (
                            <p className="text-sm text-muted-foreground">{workout.description}</p>
                          )}
                          
                          {workout.exercises && workout.exercises.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-muted-foreground mb-2">WORKOUT STRUCTURE</p>
                              <div className="space-y-1">
                                {workout.exercises.map((step: any, idx: number) => {
                                  // Build duration/distance string - prioritize distance_meters for track work
                                  const metrics: string[] = []
                                  if (step.distance_meters) {
                                    metrics.push(step.distance_meters >= 1000 
                                      ? `${(step.distance_meters / 1000).toFixed(1)}km` 
                                      : `${step.distance_meters}m`)
                                  } else if (step.distance_km) {
                                    metrics.push(`${step.distance_km}km`)
                                  } else if (step.duration_minutes) {
                                    metrics.push(`${step.duration_minutes} min`)
                                  } else if (step.duration) {
                                    metrics.push(step.duration)
                                  } else if (step.distance) {
                                    metrics.push(step.distance)
                                  }
                                  
                                  // Build pace string
                                  const paceStr = step.target_pace_min && step.target_pace_max 
                                    ? `${step.target_pace_min}-${step.target_pace_max}/km`
                                    : step.target_pace 
                                      ? `@ ${step.target_pace}`
                                      : ''
                                  
                                  return (
                                    <div
                                      key={idx}
                                      className={cn(
                                        'p-3 rounded-lg text-sm flex items-center justify-between',
                                        step.type === 'warmup' && 'bg-blue-500/10 border-l-4 border-blue-500',
                                        step.type === 'work' && 'bg-red-500/10 border-l-4 border-red-500',
                                        step.type === 'recovery' && 'bg-green-500/10 border-l-4 border-green-500',
                                        step.type === 'cooldown' && 'bg-purple-500/10 border-l-4 border-purple-500',
                                        !['warmup', 'work', 'recovery', 'cooldown'].includes(step.type) && 'bg-muted/50 border-l-4 border-muted'
                                      )}
                                    >
                                      <div className="flex items-center gap-2">
                                        <span className="font-semibold capitalize">{step.type || 'Step'}</span>
                                        {step.description && <span className="text-muted-foreground">- {step.description}</span>}
                                      </div>
                                      <div className="flex items-center gap-3">
                                        {metrics.length > 0 && (
                                          <span className="text-sm font-semibold px-2 py-0.5 rounded bg-white/10">
                                            {metrics.join(' ')}
                                          </span>
                                        )}
                                        {paceStr && (
                                          <span className="text-sm text-muted-foreground">
                                            {paceStr}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}

                          {workout.supplementary && workout.supplementary.length > 0 && (
                            <div>
                              <p className="text-xs font-semibold text-orange-400 mb-2">+ SUPPLEMENTARY ACTIVITIES</p>
                              <div className="grid grid-cols-2 gap-2">
                                {workout.supplementary.map((sup: any, idx: number) => {
                                  const activityName = (sup.type || sup.activity || '').toLowerCase()
                                  const icon = activityName.includes('wim') || activityName.includes('breath') ? '🧘‍♂️' :
                                               activityName.includes('mobility') ? '🔄' :
                                               activityName.includes('yoga') || activityName.includes('stretch') ? '🧘' :
                                               activityName.includes('cold') || activityName.includes('plunge') ? '❄️' :
                                               activityName.includes('gym') || activityName.includes('strength') ? '🏋️' :
                                               activityName.includes('sauna') ? '🔥' : '✨'
                                  
                                  return (
                                    <div key={idx} className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center gap-2">
                                      <span className="text-lg">{icon}</span>
                                      <div>
                                        <p className="text-xs font-medium">{sup.type || sup.activity}</p>
                                        <p className="text-xs text-muted-foreground">{sup.timing} • {sup.duration || sup.duration_minutes || 15}min</p>
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                          
                          {/* Send to Garmin Button */}
                          <div className="flex gap-2 pt-2 border-t border-border">
                            <SendWorkoutButton workout={workout} />
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

// Individual Send to Garmin Button
function SendWorkoutButton({ workout }: { workout: any }) {
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSend = async () => {
    setSending(true)
    try {
      // Map workout steps/exercises to the format expected by backend
      const steps = workout.exercises || workout.steps || []
      const formattedSteps = steps.map((step: any) => ({
        type: step.type || 'active',
        duration_minutes: step.duration_minutes || null,
        distance_meters: step.distance_meters || null,
        target_type: step.target_pace_min ? 'pace' : 'open',
        target_pace_min: step.target_pace_min || null,
        target_pace_max: step.target_pace_max || null,
        description: step.description || '',
      }))
      
      await workoutsAPI.sendToGarmin({
        title: workout.title || 'Workout',
        type: workout.workout_type || workout.type || 'running',
        duration_minutes: workout.duration_minutes || 30,
        steps: formattedSteps,
        description: workout.description || workout.title || 'Training workout',
      })
      setSent(true)
    } catch (err) {
      console.error('Failed to send workout:', err)
    } finally {
      setSending(false)
    }
  }

  return (
    <button
      onClick={handleSend}
      disabled={sending || sent}
      className={cn(
        'flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all',
        sent
          ? 'bg-green-500/20 text-green-400'
          : 'bg-primary/10 text-primary hover:bg-primary/20'
      )}
    >
      {sending ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : sent ? (
        <Check className="w-4 h-4" />
      ) : (
        <Send className="w-4 h-4" />
      )}
      {sent ? 'Sent to Garmin' : 'Send to Garmin'}
    </button>
  )
}
