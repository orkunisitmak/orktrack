import { useState } from 'react'
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
} from 'lucide-react'
import { aiAPI, healthAPI, activitiesAPI, workoutsAPI } from '@/lib/api'
import { cn, formatDuration } from '@/lib/utils'

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const GOALS = [
  { id: 'general', name: 'General Fitness', icon: '💪', desc: 'Balanced training', hasTime: false },
  { id: '5k', name: '5K Race', icon: '🏃', desc: 'Speed focus', hasTime: true, distance: 5, placeholder: '25:00', examples: ['18:00', '20:00', '22:00', '25:00', '30:00'] },
  { id: '10k', name: '10K Race', icon: '🏃‍♂️', desc: 'Speed endurance', hasTime: true, distance: 10, placeholder: '50:00', examples: ['38:00', '42:00', '45:00', '50:00', '55:00'] },
  { id: 'half', name: 'Half Marathon', icon: '🏅', desc: 'Endurance', hasTime: true, distance: 21.0975, placeholder: '1:45:00', examples: ['1:25:00', '1:30:00', '1:45:00', '2:00:00'] },
  { id: 'full', name: 'Marathon', icon: '🏆', desc: 'Long distance', hasTime: true, distance: 42.195, placeholder: '3:45:00', examples: ['2:59:00', '3:15:00', '3:30:00', '4:00:00'] },
  { id: 'weight_loss', name: 'Weight Loss', icon: '⚖️', desc: 'Calorie burn', hasTime: false },
]

// Convert time string (MM:SS or H:MM:SS) to seconds
const parseTimeToSeconds = (time: string): number => {
  const parts = time.split(':').map(Number)
  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  } else if (parts.length === 2) {
    return parts[0] * 60 + parts[1]
  }
  return 0
}

// Format seconds to time string
const formatSecondsToTime = (seconds: number): string => {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

// Calculate VDOT from race time and distance (simplified Daniels formula)
const calculateVDOT = (distanceKm: number, timeSeconds: number): number => {
  // Pace in min/km
  const paceMinPerKm = (timeSeconds / 60) / distanceKm
  
  // Simplified VDOT estimation based on pace
  // These are approximate values from Jack Daniels tables
  if (paceMinPerKm < 3.0) return 80
  if (paceMinPerKm < 3.2) return 75
  if (paceMinPerKm < 3.4) return 70
  if (paceMinPerKm < 3.6) return 67
  if (paceMinPerKm < 3.8) return 63
  if (paceMinPerKm < 4.0) return 60
  if (paceMinPerKm < 4.2) return 57
  if (paceMinPerKm < 4.4) return 54
  if (paceMinPerKm < 4.6) return 51
  if (paceMinPerKm < 4.8) return 49
  if (paceMinPerKm < 5.0) return 47
  if (paceMinPerKm < 5.2) return 45
  if (paceMinPerKm < 5.4) return 43
  if (paceMinPerKm < 5.6) return 41
  if (paceMinPerKm < 5.8) return 39
  if (paceMinPerKm < 6.0) return 38
  if (paceMinPerKm < 6.2) return 36
  if (paceMinPerKm < 6.5) return 35
  if (paceMinPerKm < 7.0) return 33
  if (paceMinPerKm < 7.5) return 30
  if (paceMinPerKm < 8.0) return 28
  return 25
}

const SUPPLEMENTARY_ACTIVITIES = [
  { 
    id: 'wim_hof', 
    name: 'Wim Hof Breathing', 
    icon: '🧊', 
    desc: 'Cold exposure prep & stress relief',
    optimalTiming: 'Morning (fasted) or 2h before bed',
    benefits: 'Reduces stress, improves focus, enhances cold tolerance'
  },
  { 
    id: 'mobility', 
    name: 'Mobility Work', 
    icon: '🔄', 
    desc: 'Joint health & range of motion',
    optimalTiming: 'Morning or pre-workout',
    benefits: 'Injury prevention, better movement quality'
  },
  { 
    id: 'yoga', 
    name: 'Yoga / Stretching', 
    icon: '🧘', 
    desc: 'Flexibility & recovery',
    optimalTiming: 'Evening or 6h+ after intense workout',
    benefits: 'Enhanced recovery, flexibility, stress relief'
  },
  { 
    id: 'cold_plunge', 
    name: 'Cold Plunge', 
    icon: '❄️', 
    desc: 'Recovery & adaptation',
    optimalTiming: '6h+ after strength/running (not immediately after)',
    benefits: 'Reduces inflammation, mental resilience'
  },
  { 
    id: 'gym', 
    name: 'Gym / Strength', 
    icon: '🏋️', 
    desc: 'Strength & power',
    optimalTiming: 'Separate from running or 6h+ gap',
    benefits: 'Running economy, injury prevention, power'
  },
]

export default function Planner() {
  const [selectedGoal, setSelectedGoal] = useState(GOALS[0])
  const [goalTime, setGoalTime] = useState<string>('')
  const [weekPlan, setWeekPlan] = useState<any>(null)
  const [monthPlan, setMonthPlan] = useState<any>(null)
  const [expandedDay, setExpandedDay] = useState<string | null>(null)
  const [planType, setPlanType] = useState<'week' | 'month'>('week')
  const [showPinnedPlans, setShowPinnedPlans] = useState(false)
  const [showSupplementary, setShowSupplementary] = useState(false)
  // Supplementary activities with frequency (times per week, 0 = disabled)
  const [supplementaryFrequency, setSupplementaryFrequency] = useState<Record<string, number>>({})
  const queryClient = useQueryClient()

  const toggleSupplementary = (id: string) => {
    setSupplementaryFrequency(prev => {
      if (prev[id] && prev[id] > 0) {
        // Disable it
        const { [id]: _, ...rest } = prev
        return rest
      } else {
        // Enable with default frequency of 7 (every day)
        return { ...prev, [id]: 7 }
      }
    })
  }

  const setSupplementaryCount = (id: string, count: number) => {
    if (count <= 0) {
      setSupplementaryFrequency(prev => {
        const { [id]: _, ...rest } = prev
        return rest
      })
    } else {
      setSupplementaryFrequency(prev => ({ ...prev, [id]: Math.min(7, count) }))
    }
  }

  // Get list of selected supplementary IDs for API
  const selectedSupplementary = Object.entries(supplementaryFrequency)
    .filter(([_, freq]) => freq > 0)
    .map(([id]) => id)

  // Calculate VDOT and target pace from goal time
  const goalVDOT = selectedGoal.hasTime && goalTime && selectedGoal.distance
    ? calculateVDOT(selectedGoal.distance, parseTimeToSeconds(goalTime))
    : null

  // Calculate target race pace
  const targetPace = selectedGoal.hasTime && goalTime && selectedGoal.distance
    ? formatSecondsToTime(parseTimeToSeconds(goalTime) / selectedGoal.distance)
    : null

  // Build goal string for API
  const getGoalString = () => {
    if (selectedGoal.hasTime && goalTime) {
      return `${selectedGoal.name} in ${goalTime}`
    }
    return selectedGoal.name
  }

  // Get current health status for context
  const { data: healthSummary } = useQuery({
    queryKey: ['health-summary-planner'],
    queryFn: () => healthAPI.getSummary(7),
  })

  const { data: recentActivities } = useQuery({
    queryKey: ['recent-activities-planner'],
    queryFn: () => activitiesAPI.getRecent(14),
  })

  const { data: bodyBattery } = useQuery({
    queryKey: ['body-battery'],
    queryFn: () => healthAPI.getBodyBattery(),
  })

  // Get today's readiness for autoregulation
  const { data: todayReadiness } = useQuery({
    queryKey: ['today-readiness'],
    queryFn: () => aiAPI.getTodayReadiness(),
  })

  // Get pinned plans
  const { data: pinnedPlans, refetch: refetchPinnedPlans } = useQuery({
    queryKey: ['pinned-plans'],
    queryFn: () => aiAPI.getPinnedPlans(),
  })

  const generateWeekMutation = useMutation({
    mutationFn: () =>
      aiAPI.generateWeekPlan({
        primary_goal: getGoalString(),
        supplementary_activities: selectedSupplementary,
        supplementary_frequency: supplementaryFrequency,
        goal_time: selectedGoal.hasTime ? goalTime : undefined,
        goal_distance_km: selectedGoal.hasTime ? selectedGoal.distance : undefined,
        target_vdot: goalVDOT || undefined,
      }),
    onSuccess: (data) => {
      setWeekPlan(data)
      setMonthPlan(null)
      setPlanType('week')
    },
  })

  const generateMonthMutation = useMutation({
    mutationFn: () =>
      aiAPI.generateMonthPlan({
        primary_goal: getGoalString(),
        training_phase: 'Build Phase',
        supplementary_activities: selectedSupplementary,
        supplementary_frequency: supplementaryFrequency,
        goal_time: selectedGoal.hasTime ? goalTime : undefined,
        goal_distance_km: selectedGoal.hasTime ? selectedGoal.distance : undefined,
        target_vdot: goalVDOT || undefined,
      }),
    onSuccess: (data) => {
      setMonthPlan(data)
      setWeekPlan(null)
      setPlanType('month')
    },
  })

  const pinPlanMutation = useMutation({
    mutationFn: (planData: { plan_type: string; plan_data: any }) =>
      aiAPI.pinPlan(planData),
    onSuccess: () => {
      refetchPinnedPlans()
      alert('Plan pinned successfully!')
    },
  })

  const autoMatchMutation = useMutation({
    mutationFn: () => aiAPI.autoMatchActivities(),
    onSuccess: (data) => {
      refetchPinnedPlans()
      if (data.matched_count > 0) {
        alert(`Matched ${data.matched_count} activities to scheduled workouts!`)
      } else {
        alert('No new activities to match')
      }
    },
  })

  // Calculate fitness indicators from data
  const avgHR = healthSummary?.avg_resting_hr || 60
  const avgSleep = healthSummary?.avg_sleep_hours || 7
  const bodyBatteryValue = bodyBattery?.body_battery_high || 70
  const totalActivities = recentActivities?.total || 0

  // Estimate fitness level based on resting HR
  const getFitnessLevel = () => {
    if (avgHR < 50) return { level: 'Elite', color: 'text-green-500' }
    if (avgHR < 55) return { level: 'Excellent', color: 'text-green-500' }
    if (avgHR < 60) return { level: 'Good', color: 'text-blue-500' }
    if (avgHR < 70) return { level: 'Average', color: 'text-yellow-500' }
    return { level: 'Developing', color: 'text-orange-500' }
  }

  const fitnessLevel = getFitnessLevel()

  // Estimate readiness
  const getReadiness = () => {
    if (bodyBatteryValue >= 70 && avgSleep >= 7) return { status: 'Ready', color: 'text-green-500' }
    if (bodyBatteryValue >= 50) return { status: 'Moderate', color: 'text-yellow-500' }
    return { status: 'Recovery Needed', color: 'text-red-500' }
  }

  const readiness = getReadiness()

  const currentPlan = planType === 'week' ? weekPlan : monthPlan
  const isGenerating = generateWeekMutation.isPending || generateMonthMutation.isPending

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">AI Training Planner</h1>
          <p className="text-muted-foreground">
            Generate personalized week or month training plans based on your health data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPinnedPlans(!showPinnedPlans)}
            className={cn(
              'px-4 py-2 rounded-xl flex items-center gap-2 transition-colors',
              showPinnedPlans ? 'bg-primary text-white' : 'bg-muted hover:bg-muted/80'
            )}
          >
            <ListChecks className="w-4 h-4" />
            My Plans ({pinnedPlans?.plans?.length || 0})
          </button>
          <button
            onClick={() => autoMatchMutation.mutate()}
            disabled={autoMatchMutation.isPending}
            className="px-4 py-2 rounded-xl bg-green-500/20 text-green-500 hover:bg-green-500/30 flex items-center gap-2"
          >
            {autoMatchMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Sync Activities
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
          <div>
            <p className={cn(
              'font-semibold',
              todayReadiness.should_rest ? 'text-red-500' : 'text-yellow-500'
            )}>
              Today's Adjustment Required
            </p>
            <p className="text-sm text-muted-foreground">{todayReadiness.adjustment_reason}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Body Battery: {todayReadiness.body_battery || 'N/A'} | 
              Sleep Score: {todayReadiness.sleep_score || 'N/A'} | 
              HRV: {todayReadiness.hrv_status}
            </p>
          </div>
        </motion.div>
      )}

      {/* Pinned Plans View */}
      {showPinnedPlans && pinnedPlans?.plans && pinnedPlans.plans.length > 0 && (
        <div className="p-6 rounded-2xl bg-card border border-border">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Pin className="w-5 h-5 text-primary" />
            Your Pinned Plans
          </h3>
          <div className="space-y-3">
            {pinnedPlans.plans.map((plan: any) => (
              <div key={plan.id} className="p-4 rounded-xl bg-muted/30 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{plan.plan_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {plan.primary_goal} • {plan.plan_type}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-primary">
                      {plan.progress_percentage?.toFixed(0) || 0}%
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {plan.completed_workouts}/{plan.total_workouts} workouts
                    </p>
                  </div>
                </div>
                <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${plan.progress_percentage || 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Your Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatusCard
          icon={Heart}
          label="Fitness Level"
          value={fitnessLevel.level}
          detail={`${avgHR} bpm resting`}
          color="red"
        />
        <StatusCard
          icon={Zap}
          label="Today's Readiness"
          value={todayReadiness?.readiness_score ? `${todayReadiness.readiness_score}%` : readiness.status}
          detail={todayReadiness?.body_battery ? `Battery: ${todayReadiness.body_battery}%` : `Battery: ${bodyBatteryValue}%`}
          color="yellow"
        />
        <StatusCard
          icon={Moon}
          label="Avg Sleep"
          value={`${avgSleep.toFixed(1)}h`}
          detail="Last 7 days"
          color="purple"
        />
        <StatusCard
          icon={Activity}
          label="Recent Workouts"
          value={totalActivities.toString()}
          detail="Last 14 days"
          color="green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Goal Selection */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-2xl bg-card border border-border">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Your Goal
            </h3>
            
            {/* Goal Time Toggle - Always visible */}
            <div className="mb-4 p-3 rounded-xl bg-muted/30 border border-border">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  🎯 Set Target Time
                </label>
                <button
                  onClick={() => setGoalTime(goalTime ? '' : (selectedGoal.placeholder || ''))}
                  className={cn(
                    'relative w-12 h-6 rounded-full transition-colors',
                    goalTime ? 'bg-primary' : 'bg-muted-foreground/30'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                      goalTime ? 'translate-x-7' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>
              
              {/* Goal Time Input - shown when toggle is on AND goal has time */}
              {goalTime !== '' && selectedGoal.hasTime && (
                <div className="space-y-3 mt-3 pt-3 border-t border-border/50">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={goalTime}
                      onChange={(e) => setGoalTime(e.target.value)}
                      placeholder={selectedGoal.placeholder}
                      className="flex-1 px-3 py-2 rounded-lg bg-card border border-border text-lg font-mono focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                    <span className="text-sm text-muted-foreground">{selectedGoal.name}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedGoal.examples?.map((ex) => (
                      <button
                        key={ex}
                        onClick={() => setGoalTime(ex)}
                        className={cn(
                          'px-2 py-1 rounded-md text-xs font-mono transition-colors',
                          goalTime === ex 
                            ? 'bg-primary text-white' 
                            : 'bg-muted hover:bg-muted/80'
                        )}
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                  
                  {/* VDOT Preview */}
                  {goalVDOT && targetPace && (
                    <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/30">
                      <div className="flex items-center justify-between text-xs">
                        <span>VDOT: <strong className="text-green-500">{goalVDOT}</strong></span>
                        <span>Pace: <strong className="text-green-500 font-mono">{targetPace}/km</strong></span>
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {goalTime !== '' && !selectedGoal.hasTime && (
                <p className="text-xs text-muted-foreground mt-2">
                  Select a race goal (5K, 10K, Half, Marathon) to set a target time
                </p>
              )}
            </div>

            {/* Goal Selection Buttons */}
            <div className="space-y-2">
              {GOALS.map((goal) => (
                <button
                  key={goal.id}
                  onClick={() => {
                    setSelectedGoal(goal)
                    if (!goal.hasTime) setGoalTime('')
                  }}
                  className={cn(
                    'w-full p-3 rounded-xl text-left transition-all',
                    selectedGoal.id === goal.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted/30 hover:bg-muted/50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{goal.icon}</span>
                    <div className="flex-1">
                      <p className="font-medium">{goal.name}</p>
                      <p
                        className={cn(
                          'text-xs',
                          selectedGoal.id === goal.id
                            ? 'text-primary-foreground/70'
                            : 'text-muted-foreground'
                        )}
                      >
                        {goal.desc}
                      </p>
                    </div>
                    {goal.hasTime && (
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full',
                        selectedGoal.id === goal.id
                          ? 'bg-white/20 text-white'
                          : 'bg-muted text-muted-foreground'
                      )}>
                        ⏱️
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Supplementary Activities Toggle */}
          <div className="rounded-2xl bg-card border border-border overflow-hidden">
            <button
              onClick={() => setShowSupplementary(!showSupplementary)}
              className="w-full p-4 flex items-center justify-between hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-orange-500" />
                <div className="text-left">
                  <h3 className="font-semibold">Add to Plan</h3>
                  {selectedSupplementary.length > 0 && (
                    <p className="text-xs text-orange-500">
                      {selectedSupplementary.length} activities • {Object.values(supplementaryFrequency).reduce((a, b) => a + b, 0)} sessions/week
                    </p>
                  )}
                </div>
              </div>
              <ChevronDown className={cn(
                'w-5 h-5 text-muted-foreground transition-transform',
                showSupplementary && 'rotate-180'
              )} />
            </button>
            
            <AnimatePresence>
              {showSupplementary && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="p-4 pt-0 space-y-2">
                    <p className="text-xs text-muted-foreground mb-3">
                      Select activities and set frequency per week
                    </p>
                    {SUPPLEMENTARY_ACTIVITIES.map((activity) => {
                      const frequency = supplementaryFrequency[activity.id] || 0
                      const isSelected = frequency > 0
                      return (
                        <div
                          key={activity.id}
                          className={cn(
                            'w-full p-3 rounded-xl text-left transition-all border',
                            isSelected
                              ? 'bg-orange-500/10 border-orange-500/50'
                              : 'bg-muted/20 border-transparent hover:bg-muted/40'
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => toggleSupplementary(activity.id)}
                              className={cn(
                                'w-5 h-5 rounded flex items-center justify-center text-sm border-2 transition-colors flex-shrink-0',
                                isSelected 
                                  ? 'bg-orange-500 border-orange-500 text-white' 
                                  : 'border-muted-foreground/30 hover:border-orange-400'
                              )}
                            >
                              {isSelected && <Check className="w-3 h-3" />}
                            </button>
                            <div className="flex-1 min-w-0 flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span>{activity.icon}</span>
                                <span className="text-sm font-medium">{activity.name}</span>
                              </div>
                              {isSelected && (
                                <div className="flex items-center gap-1 bg-orange-500/20 rounded-lg px-2 py-1">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setSupplementaryCount(activity.id, frequency - 1)
                                    }}
                                    className="w-5 h-5 rounded flex items-center justify-center text-orange-600 hover:bg-orange-500/30 text-sm font-bold"
                                  >
                                    −
                                  </button>
                                  <span className="w-6 text-center text-xs font-bold text-orange-600">
                                    {frequency}x
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setSupplementaryCount(activity.id, frequency + 1)
                                    }}
                                    disabled={frequency >= 7}
                                    className="w-5 h-5 rounded flex items-center justify-center text-orange-600 hover:bg-orange-500/30 text-sm font-bold disabled:opacity-30"
                                  >
                                    +
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Generate buttons */}
          <div className="space-y-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => generateWeekMutation.mutate()}
              disabled={isGenerating}
              className={cn(
                'w-full py-4 px-6 rounded-xl font-semibold',
                'bg-gradient-to-r from-primary to-purple-500',
                'text-white shadow-lg shadow-primary/30',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'flex items-center justify-center gap-2'
              )}
            >
              {generateWeekMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating week plan...
                </>
              ) : (
                <>
                  <Calendar className="w-5 h-5" />
                  Generate Week Plan
                </>
              )}
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => generateMonthMutation.mutate()}
              disabled={isGenerating}
              className={cn(
                'w-full py-4 px-6 rounded-xl font-semibold',
                'bg-gradient-to-r from-orange-500 to-red-500',
                'text-white shadow-lg shadow-orange-500/30',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'flex items-center justify-center gap-2'
              )}
            >
              {generateMonthMutation.isPending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating month plan...
                </>
              ) : (
                <>
                  <CalendarDays className="w-5 h-5" />
                  Generate Month Plan
                </>
              )}
            </motion.button>
          </div>

          {/* Info box */}
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/20">
            <div className="flex items-start gap-3">
              <Brain className="w-5 h-5 text-primary mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-primary mb-1">AI-Powered Planning</p>
                <p className="text-muted-foreground">
                  Plans use 80/20 polarized training with VDOT-calculated paces. 
                  Today's workout is adjusted based on your current readiness - 
                  future days are baseline and will be adjusted daily.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Plan Display */}
        <div className="lg:col-span-2">
          {currentPlan ? (
            planType === 'month' && monthPlan ? (
              <MonthPlanDisplay
                plan={monthPlan}
                expandedDay={expandedDay}
                setExpandedDay={setExpandedDay}
                onRegenerate={() => generateMonthMutation.mutate()}
                isRegenerating={generateMonthMutation.isPending}
                onPin={() => pinPlanMutation.mutate({ plan_type: 'month', plan_data: monthPlan })}
                isPinning={pinPlanMutation.isPending}
              />
            ) : (
              <WeekPlanDisplay 
                plan={weekPlan} 
                expandedDay={expandedDay}
                setExpandedDay={setExpandedDay}
                onRegenerate={() => generateWeekMutation.mutate()}
                isRegenerating={generateWeekMutation.isPending}
                onPin={() => pinPlanMutation.mutate({ plan_type: 'week', plan_data: weekPlan })}
                isPinning={pinPlanMutation.isPending}
                recentActivities={recentActivities?.activities || []}
                onSendToGarmin={async (workout) => {
                  try {
                    const result = await workoutsAPI.sendToGarmin({
                      title: workout.title,
                      description: workout.description || '',
                      type: workout.type || 'running',
                      duration_minutes: workout.duration_minutes || 30,
                      steps: workout.steps,
                      target_hr_zone: workout.target_hr_zone,
                    })
                    
                    if (result.success) {
                      // Show success with link to create in Garmin Connect
                      if (confirm(`${result.message}\n\n${result.note}\n\nOpen Garmin Connect to create this workout?`)) {
                        window.open(result.manual_creation_url, '_blank')
                      }
                    }
                  } catch (error) {
                    alert('Failed to prepare workout for Garmin')
                  }
                }}
              />
            )
          ) : (
            <div className="h-full min-h-[500px] flex items-center justify-center rounded-2xl bg-card border border-border border-dashed">
              <div className="text-center p-8">
                <Calendar className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-medium mb-2">No Plan Generated</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  Select your goal and generate a week or month plan based on your health data.
                  The AI will create personalized workouts with specific paces from your VDOT score.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusCard({ 
  icon: Icon, 
  label, 
  value, 
  detail, 
  color 
}: { 
  icon: React.ElementType
  label: string
  value: string
  detail: string
  color: 'red' | 'yellow' | 'purple' | 'green'
}) {
  const colorClasses = {
    red: 'bg-red-500/20 text-red-500',
    yellow: 'bg-yellow-500/20 text-yellow-500',
    purple: 'bg-purple-500/20 text-purple-500',
    green: 'bg-green-500/20 text-green-500',
  }

  return (
    <div className="p-4 rounded-xl bg-card border border-border">
      <div className={cn('p-2 rounded-lg inline-flex mb-2', colorClasses[color])}>
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{detail}</p>
    </div>
  )
}

function WeekPlanDisplay({ 
  plan, 
  expandedDay, 
  setExpandedDay,
  onRegenerate,
  isRegenerating,
  onPin,
  isPinning,
  recentActivities = [],
  onSendToGarmin,
}: { 
  plan: any
  expandedDay: string | null
  setExpandedDay: (day: string | null) => void
  onRegenerate: () => void
  isRegenerating: boolean
  onPin?: () => void
  isPinning?: boolean
  recentActivities?: any[]
  onSendToGarmin?: (workout: any) => void
}) {
  const todayAutoregulation = plan.today_autoregulation || {}
  const hasTodayAdjustment = todayAutoregulation.applied

  // Match workouts with activities
  const getMatchedActivity = (workout: any, dayIndex: number) => {
    if (!recentActivities?.length) return null
    
    // Get the date for this workout (assuming plan starts from Monday of current week)
    const today = new Date()
    const startOfWeek = new Date(today)
    startOfWeek.setDate(today.getDate() - today.getDay() + 1) // Monday
    const workoutDate = new Date(startOfWeek)
    workoutDate.setDate(startOfWeek.getDate() + dayIndex)
    const dateStr = workoutDate.toISOString().split('T')[0]
    
    // Find matching activity
    return recentActivities.find(a => {
      const activityDate = a.startTimeLocal?.split('T')[0] || a.date
      if (activityDate !== dateStr) return false
      
      // Match by type
      const actType = a.classifiedType || a.activityType?.typeKey || 'other'
      const workoutType = workout.type?.toLowerCase()
      
      if (workoutType?.includes('run') && actType.includes('run')) return true
      if (workoutType?.includes('strength') && (actType.includes('strength') || actType.includes('gym'))) return true
      if (workoutType?.includes('yoga') && actType.includes('yoga')) return true
      if (workoutType?.includes('recovery') && (actType.includes('yoga') || actType.includes('mobility'))) return true
      
      return true // Default match by date
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 rounded-2xl bg-card border border-border"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">{plan.plan_name || 'Your Week Plan'}</h2>
          <p className="text-muted-foreground text-sm">{plan.description || plan.rationale}</p>
          <div className="flex flex-wrap gap-3 mt-2">
            {plan.goal_time && (
              <span className="inline-flex items-center px-2 py-1 rounded-md bg-green-500/20 text-green-500 text-xs font-medium">
                🎯 Goal: {plan.goal_time}
              </span>
            )}
            {plan.estimated_vdot && (
              <span className="inline-flex items-center px-2 py-1 rounded-md bg-primary/20 text-primary text-xs font-medium">
                VDOT: {plan.estimated_vdot}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasTodayAdjustment && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-yellow-500/20 text-yellow-500 text-sm">
              <AlertTriangle className="w-4 h-4" />
              Today adjusted
            </div>
          )}
          {onPin && (
            <button
              onClick={onPin}
              disabled={isPinning}
              className="p-2 rounded-lg hover:bg-primary/20 text-primary transition-colors disabled:opacity-50"
              title="Pin this plan"
            >
              {isPinning ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Pin className="w-5 h-5" />
              )}
            </button>
          )}
          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-5 h-5', isRegenerating && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Today's adjustment note */}
      {hasTodayAdjustment && todayAutoregulation.reason && (
        <div className="mb-6 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
          <p className="text-sm text-yellow-600 font-medium mb-1">Today's Adjustment</p>
          <p className="text-sm text-muted-foreground">{todayAutoregulation.reason}</p>
          {todayAutoregulation.original_workout && (
            <p className="text-xs text-muted-foreground mt-1">
              Original: {todayAutoregulation.original_workout} → Now: {todayAutoregulation.adjusted_workout}
            </p>
          )}
        </div>
      )}

      {/* Week summary */}
      {plan.weekly_summary && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-muted/30 text-center">
            <p className="text-2xl font-bold">{plan.weekly_summary.total_workouts || plan.workouts?.length || 0}</p>
            <p className="text-sm text-muted-foreground">Workouts</p>
          </div>
          <div className="p-4 rounded-xl bg-muted/30 text-center">
            <p className="text-2xl font-bold">
              {plan.weekly_summary.total_duration_hours?.toFixed(1) || '--'}h
            </p>
            <p className="text-sm text-muted-foreground">Total Time</p>
          </div>
          <div className="p-4 rounded-xl bg-muted/30 text-center">
            <p className="text-2xl font-bold">
              {plan.weekly_summary.estimated_distance_km?.toFixed(0) || '--'} km
            </p>
            <p className="text-sm text-muted-foreground">Distance</p>
          </div>
        </div>
      )}

      {/* Intensity distribution */}
      {plan.intensity_distribution && (
        <div className="mb-6">
          <p className="text-xs text-muted-foreground mb-2">Intensity Distribution (80/20 Polarized)</p>
          <div className="flex gap-2 h-3 rounded-full overflow-hidden">
            <div 
              className="bg-green-500 rounded-full" 
              style={{ width: `${plan.intensity_distribution.low || 80}%` }}
              title={`Low: ${plan.intensity_distribution.low}%`}
            />
            <div 
              className="bg-yellow-500 rounded-full" 
              style={{ width: `${plan.intensity_distribution.moderate || 10}%` }}
              title={`Moderate: ${plan.intensity_distribution.moderate}%`}
            />
            <div 
              className="bg-red-500 rounded-full" 
              style={{ width: `${plan.intensity_distribution.high || 10}%` }}
              title={`High: ${plan.intensity_distribution.high}%`}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>Low ({plan.intensity_distribution.low || 80}%)</span>
            <span>Moderate ({plan.intensity_distribution.moderate || 10}%)</span>
            <span>High ({plan.intensity_distribution.high || 10}%)</span>
          </div>
        </div>
      )}

      {/* Daily workouts */}
      <div className="space-y-3">
        {(plan.workouts || []).map((workout: any, index: number) => {
          const isExpanded = expandedDay === workout.day
          const isRest = workout.type === 'rest' || workout.title?.toLowerCase().includes('rest')
          const matchedActivity = getMatchedActivity(workout, index)
          const isCompleted = !!matchedActivity

          return (
            <motion.div
              key={workout.day || index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className={cn(
                'rounded-xl border overflow-hidden cursor-pointer transition-all',
                isCompleted && 'border-green-500/50 bg-green-500/5',
                isRest && !isCompleted && 'bg-muted/20 border-muted',
                !isRest && !isCompleted && 'bg-muted/30 border-border hover:border-primary/30',
                isExpanded && 'ring-2 ring-primary/30'
              )}
              onClick={() => setExpandedDay(isExpanded ? null : (workout.day || index.toString()))}
            >
              {/* Day header */}
              <div className="flex items-center gap-4 p-4">
                <div className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold relative',
                  isCompleted ? 'bg-green-500/20 text-green-500' : isRest ? 'bg-muted text-muted-foreground' : 'bg-primary/20 text-primary'
                )}>
                  {(workout.day || DAYS_OF_WEEK[index])?.slice(0, 2)}
                  {isCompleted && (
                    <div className="absolute -top-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">{workout.day || DAYS_OF_WEEK[index]}</p>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">{workout.title}</p>
                    {isCompleted && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-500 font-medium">
                        ✓ Done
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  {workout.duration_minutes && (
                    <div className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="w-4 h-4" />
                      <span>{formatDuration(workout.duration_minutes)}</span>
                    </div>
                  )}
                  <span className={cn(
                    'px-2 py-1 rounded-full text-xs font-medium',
                    workout.intensity === 'low' && 'bg-green-500/20 text-green-500',
                    workout.intensity === 'moderate' && 'bg-yellow-500/20 text-yellow-500',
                    workout.intensity === 'high' && 'bg-red-500/20 text-red-500',
                    isRest && 'bg-muted text-muted-foreground'
                  )}>
                    {workout.intensity || (isRest ? 'Rest' : 'Mixed')}
                  </span>
                  <ChevronRight className={cn(
                    'w-5 h-5 text-muted-foreground transition-transform',
                    isExpanded && 'rotate-90'
                  )} />
                </div>
              </div>

              {/* Expanded details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="px-4 pb-4 pt-2 border-t border-border/50">
                      <p className="text-sm mb-4">{workout.description}</p>
                      
                      {/* Workout Steps with Paces */}
                      {workout.steps && workout.steps.length > 0 && (
                        <div className="mb-4 space-y-2">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                            Workout Structure
                          </p>
                          {workout.steps.map((step: any, stepIdx: number) => (
                            <div 
                              key={stepIdx}
                              className={cn(
                                'p-3 rounded-lg border text-sm',
                                step.type === 'warmup' && 'bg-blue-500/10 border-blue-500/30',
                                step.type === 'work' && 'bg-red-500/10 border-red-500/30',
                                step.type === 'recovery' && 'bg-green-500/10 border-green-500/30',
                                step.type === 'cooldown' && 'bg-purple-500/10 border-purple-500/30',
                              )}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className={cn(
                                  'text-xs font-semibold uppercase',
                                  step.type === 'warmup' && 'text-blue-500',
                                  step.type === 'work' && 'text-red-500',
                                  step.type === 'recovery' && 'text-green-500',
                                  step.type === 'cooldown' && 'text-purple-500',
                                )}>
                                  {step.type}
                                </span>
                                {step.duration_value && (
                                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Timer className="w-3 h-3" />
                                    {step.duration_value}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm">{step.description}</p>
                              {(step.target_pace_min || step.target_pace_max) && (
                                <p className="text-xs font-mono mt-1 text-primary">
                                  Target: {step.target_pace_min}{step.target_pace_max && step.target_pace_min !== step.target_pace_max ? ` - ${step.target_pace_max}` : ''} /km
                                </p>
                              )}
                              {step.target_hr_bpm && (
                                <p className="text-xs text-red-400 mt-0.5">
                                  HR: {step.target_hr_bpm}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {workout.key_focus && (
                        <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/10 text-primary text-sm mb-4">
                          <CheckCircle className="w-4 h-4" />
                          <span className="font-medium">Focus: {workout.key_focus}</span>
                        </div>
                      )}

                      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mb-4">
                        {workout.target_hr_zone && (
                          <div className="flex items-center gap-2">
                            <Heart className="w-4 h-4 text-red-500" />
                            {workout.target_hr_zone}
                            {workout.target_hr_bpm && <span className="text-xs">({workout.target_hr_bpm})</span>}
                          </div>
                        )}
                        {workout.estimated_distance_km && (
                          <div className="flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-green-500" />
                            {workout.estimated_distance_km} km
                          </div>
                        )}
                        {workout.optimal_time && (
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-blue-500" />
                            {workout.optimal_time}
                          </div>
                        )}
                      </div>

                      {/* Supplementary Activities */}
                      {workout.supplementary && workout.supplementary.length > 0 && (
                        <div className="mb-4 p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
                          <p className="text-xs font-semibold text-orange-500 uppercase tracking-wide mb-2">
                            + Supplementary Activities
                          </p>
                          <div className="space-y-2">
                            {workout.supplementary.map((supp: any, suppIdx: number) => {
                              const suppIcon: Record<string, string> = {
                                wim_hof: '🧊',
                                mobility: '🔄',
                                yoga: '🧘',
                                cold_plunge: '❄️',
                                gym: '🏋️',
                              }
                              return (
                                <div key={suppIdx} className="text-sm flex items-start gap-2">
                                  <span className="text-lg">{suppIcon[supp.type] || '✨'}</span>
                                  <div>
                                    <p className="font-medium">
                                      {supp.type?.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      ⏰ {supp.timing} • {supp.duration_minutes} min
                                    </p>
                                    {supp.notes && (
                                      <p className="text-xs text-orange-600 mt-0.5">{supp.notes}</p>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {/* Completed Activity Details */}
                      {isCompleted && matchedActivity && (
                        <div className="mb-4 p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                          <p className="text-xs font-semibold text-green-500 uppercase tracking-wide mb-3 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4" />
                            Completed Activity
                          </p>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            {matchedActivity.duration && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Duration</p>
                                <p className="font-bold">{formatDuration(matchedActivity.duration / 60)}</p>
                              </div>
                            )}
                            {matchedActivity.distance && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Distance</p>
                                <p className="font-bold">{(matchedActivity.distance / 1000).toFixed(2)} km</p>
                              </div>
                            )}
                            {matchedActivity.averageHR && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Avg HR</p>
                                <p className="font-bold text-red-500">{matchedActivity.averageHR} bpm</p>
                              </div>
                            )}
                            {matchedActivity.averageSpeed && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Pace</p>
                                <p className="font-bold font-mono">
                                  {Math.floor(1000 / (matchedActivity.averageSpeed * 60))}:
                                  {String(Math.floor((1000 / matchedActivity.averageSpeed) % 60)).padStart(2, '0')}/km
                                </p>
                              </div>
                            )}
                            {matchedActivity.calories && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Calories</p>
                                <p className="font-bold">{matchedActivity.calories} kcal</p>
                              </div>
                            )}
                            {(matchedActivity.aerobicTrainingEffect || matchedActivity.trainingEffectAerobic) && (
                              <div className="p-2 rounded-lg bg-card">
                                <p className="text-xs text-muted-foreground">Training Effect</p>
                                <p className="font-bold text-primary">
                                  {(matchedActivity.aerobicTrainingEffect || matchedActivity.trainingEffectAerobic)?.toFixed(1)}
                                </p>
                              </div>
                            )}
                          </div>
                          {/* Performance comparison */}
                          {workout.estimated_distance_km && matchedActivity.distance && (
                            <div className="mt-3 p-2 rounded-lg bg-card text-xs">
                              <span className="text-muted-foreground">vs Planned: </span>
                              {matchedActivity.distance / 1000 >= workout.estimated_distance_km ? (
                                <span className="text-green-500 font-medium">
                                  +{((matchedActivity.distance / 1000) - workout.estimated_distance_km).toFixed(1)} km over target ✓
                                </span>
                              ) : (
                                <span className="text-yellow-500 font-medium">
                                  {((matchedActivity.distance / 1000) - workout.estimated_distance_km).toFixed(1)} km under target
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Action buttons */}
                      {!isRest && (
                        <div className="flex gap-3 mt-4">
                          {!isCompleted && onSendToGarmin && (
                            <motion.button
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={(e) => {
                                e.stopPropagation()
                                onSendToGarmin(workout)
                              }}
                              className="flex-1 py-3 px-4 rounded-xl font-medium bg-primary text-white flex items-center justify-center gap-2"
                            >
                              <Send className="w-4 h-4" />
                              Send to Garmin
                            </motion.button>
                          )}
                          {!isCompleted && (
                            <motion.button
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              className={cn(
                                "py-3 px-4 rounded-xl font-medium bg-green-500 text-white flex items-center justify-center gap-2",
                                onSendToGarmin ? "flex-1" : "w-full"
                              )}
                            >
                              <Play className="w-4 h-4" />
                              Start Workout
                            </motion.button>
                          )}
                          {isCompleted && (
                            <div className="w-full py-3 px-4 rounded-xl font-medium bg-green-500/20 text-green-500 flex items-center justify-center gap-2">
                              <CheckCircle className="w-4 h-4" />
                              Workout Completed
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>

      {/* Weekly goals */}
      {plan.weekly_goals && plan.weekly_goals.length > 0 && (
        <div className="mt-6 p-4 rounded-xl bg-green-500/10 border border-green-500/30">
          <h4 className="font-semibold text-green-500 mb-2 flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            Weekly Goals
          </h4>
          <ul className="space-y-1">
            {plan.weekly_goals.map((goal: string, i: number) => (
              <li key={i} className="text-sm flex items-start gap-2">
                <span className="text-green-500 mt-1">•</span>
                {goal}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recovery recommendations */}
      {plan.recovery_recommendations && (
        <div className="mt-4 p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
          <h4 className="font-semibold text-purple-500 mb-2 flex items-center gap-2">
            <Moon className="w-5 h-5" />
            Recovery Tips
          </h4>
          <p className="text-sm">{plan.recovery_recommendations}</p>
        </div>
      )}

      {/* Supplementary Schedule Summary */}
      {plan.supplementary_schedule && Object.keys(plan.supplementary_schedule).length > 0 && (
        <div className="mt-6 p-4 rounded-xl bg-orange-500/10 border border-orange-500/30">
          <h4 className="font-semibold text-orange-500 mb-3 flex items-center gap-2">
            <Sparkles className="w-5 h-5" />
            Supplementary Activities Schedule
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(plan.supplementary_schedule).map(([type, schedule]: [string, any]) => {
              const suppIcons: Record<string, string> = {
                wim_hof: '🧊',
                mobility: '🔄',
                yoga: '🧘',
                cold_plunge: '❄️',
                gym: '🏋️',
              }
              return (
                <div key={type} className="p-3 rounded-lg bg-card/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{suppIcons[type] || '✨'}</span>
                    <span className="font-medium text-sm">
                      {type.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {Array.isArray(schedule) ? schedule.join(', ') : schedule}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Daily adjustment note */}
      {plan.daily_adjustment_note && (
        <div className="mt-4 p-3 rounded-lg bg-muted/30 text-xs text-muted-foreground">
          <Brain className="w-4 h-4 inline mr-2" />
          {plan.daily_adjustment_note}
        </div>
      )}
    </motion.div>
  )
}

function MonthPlanDisplay({
  plan,
  expandedDay,
  setExpandedDay,
  onRegenerate,
  isRegenerating,
  onPin,
  isPinning,
}: {
  plan: any
  expandedDay: string | null
  setExpandedDay: (day: string | null) => void
  onRegenerate: () => void
  isRegenerating: boolean
  onPin?: () => void
  isPinning?: boolean
}) {
  const [expandedWeek, setExpandedWeek] = useState<number | null>(null)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 rounded-2xl bg-card border border-border"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">{plan.plan_name || '4-Week Training Plan'}</h2>
          <p className="text-muted-foreground text-sm">{plan.mesocycle_overview}</p>
          {plan.estimated_vdot && (
            <p className="text-xs text-primary mt-1">VDOT: {plan.estimated_vdot}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onPin && (
            <button
              onClick={onPin}
              disabled={isPinning}
              className="p-2 rounded-lg hover:bg-primary/20 text-primary transition-colors disabled:opacity-50"
              title="Pin this plan"
            >
              {isPinning ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Pin className="w-5 h-5" />
              )}
            </button>
          )}
          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-5 h-5', isRegenerating && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Weeks */}
      <div className="space-y-4">
        {(plan.weeks || []).map((week: any, weekIdx: number) => {
          const isWeekExpanded = expandedWeek === weekIdx

          return (
            <div
              key={weekIdx}
              className={cn(
                'rounded-xl border overflow-hidden transition-all',
                isWeekExpanded ? 'ring-2 ring-primary/30' : 'hover:border-primary/30'
              )}
            >
              {/* Week header */}
              <div
                className="p-4 bg-muted/30 cursor-pointer flex items-center justify-between"
                onClick={() => setExpandedWeek(isWeekExpanded ? null : weekIdx)}
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
                    <span className="text-lg font-bold text-primary">W{week.week_number || weekIdx + 1}</span>
                  </div>
                  <div>
                    <p className="font-semibold">{week.week_focus || `Week ${weekIdx + 1}`}</p>
                    <p className="text-sm text-muted-foreground">
                      {week.total_workouts} workouts • {week.total_duration_hours?.toFixed(1)}h • {week.total_distance_km?.toFixed(0)} km
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {/* Week intensity distribution */}
                  {week.intensity_distribution && (
                    <div className="hidden md:flex gap-1 h-2 w-24 rounded-full overflow-hidden">
                      <div className="bg-green-500" style={{ width: `${week.intensity_distribution.low || 80}%` }} />
                      <div className="bg-yellow-500" style={{ width: `${week.intensity_distribution.moderate || 10}%` }} />
                      <div className="bg-red-500" style={{ width: `${week.intensity_distribution.high || 10}%` }} />
                    </div>
                  )}
                  <ChevronRight className={cn(
                    'w-5 h-5 text-muted-foreground transition-transform',
                    isWeekExpanded && 'rotate-90'
                  )} />
                </div>
              </div>

              {/* Week details */}
              <AnimatePresence>
                {isWeekExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 border-t border-border/50 space-y-3">
                      {/* Key sessions */}
                      {week.key_sessions && week.key_sessions.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs text-muted-foreground uppercase tracking-wide mb-2">Key Sessions</p>
                          <div className="flex flex-wrap gap-2">
                            {week.key_sessions.map((session: string, i: number) => (
                              <span key={i} className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                                {session}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Daily workouts */}
                      {(week.workouts || []).map((workout: any, dayIdx: number) => {
                        const dayKey = `${weekIdx}-${dayIdx}`
                        const isDayExpanded = expandedDay === dayKey
                        const isRest = workout.type === 'rest'

                        return (
                          <div
                            key={dayIdx}
                            className={cn(
                              'rounded-lg border overflow-hidden cursor-pointer',
                              isRest ? 'bg-muted/20 border-muted' : 'bg-muted/30 border-border',
                              isDayExpanded && 'ring-1 ring-primary/30'
                            )}
                            onClick={() => setExpandedDay(isDayExpanded ? null : dayKey)}
                          >
                            <div className="flex items-center gap-3 p-3">
                              <div className={cn(
                                'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold',
                                isRest ? 'bg-muted text-muted-foreground' : 'bg-primary/20 text-primary'
                              )}>
                                {(workout.day || DAYS_OF_WEEK[dayIdx])?.slice(0, 2)}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium truncate">{workout.title}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                {workout.duration_minutes && (
                                  <span className="text-xs text-muted-foreground">
                                    {workout.duration_minutes}min
                                  </span>
                                )}
                                <span className={cn(
                                  'px-2 py-0.5 rounded-full text-xs',
                                  workout.intensity === 'low' && 'bg-green-500/20 text-green-500',
                                  workout.intensity === 'moderate' && 'bg-yellow-500/20 text-yellow-500',
                                  workout.intensity === 'high' && 'bg-red-500/20 text-red-500',
                                )}>
                                  {workout.intensity}
                                </span>
                              </div>
                            </div>

                            {/* Day expanded */}
                            <AnimatePresence>
                              {isDayExpanded && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="overflow-hidden"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <div className="px-3 pb-3 pt-1 border-t border-border/50">
                                    <p className="text-sm text-muted-foreground mb-2">{workout.description}</p>
                                    
                                    {/* Steps */}
                                    {workout.steps && workout.steps.length > 0 && (
                                      <div className="space-y-1">
                                        {workout.steps.map((step: any, stepIdx: number) => (
                                          <div key={stepIdx} className="text-xs p-2 bg-muted/50 rounded">
                                            <span className="font-semibold text-primary">{step.type}:</span>{' '}
                                            {step.description}
                                            {(step.target_pace_min || step.target_pace_max) && (
                                              <span className="text-primary ml-1">
                                                @ {step.target_pace_min}{step.target_pace_max !== step.target_pace_min ? `-${step.target_pace_max}` : ''}/km
                                              </span>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>

      {/* Progression notes */}
      {plan.progression_notes && (
        <div className="mt-6 p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
          <h4 className="font-semibold text-blue-500 mb-2 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Progression
          </h4>
          <p className="text-sm">{plan.progression_notes}</p>
        </div>
      )}

      {/* Recovery protocol */}
      {plan.recovery_protocol && (
        <div className="mt-4 p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
          <h4 className="font-semibold text-purple-500 mb-2 flex items-center gap-2">
            <Moon className="w-5 h-5" />
            Recovery Protocol
          </h4>
          <p className="text-sm">{plan.recovery_protocol}</p>
        </div>
      )}

      {/* Adaptation guidelines */}
      {plan.adaptation_guidelines && (
        <div className="mt-4 p-3 rounded-lg bg-muted/30 text-xs text-muted-foreground">
          <Brain className="w-4 h-4 inline mr-2" />
          {plan.adaptation_guidelines}
        </div>
      )}
    </motion.div>
  )
}
