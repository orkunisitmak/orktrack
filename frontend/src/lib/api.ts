const API_BASE = '/api'

// Handle 401 errors by clearing auth state
const handle401 = () => {
  // Clear stored auth
  localStorage.removeItem('orktrack-auth')
  // Redirect to login
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (response.status === 401) {
    handle401()
    throw new Error('Authentication required')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// Auth API
export const authAPI = {
  login: (data: { email?: string; password?: string; use_saved_tokens?: boolean }) =>
    fetchAPI<{ success: boolean; user: any; message: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  status: () =>
    fetchAPI<{ authenticated: boolean; user: any }>('/auth/status'),

  logout: () =>
    fetchAPI<{ success: boolean }>('/auth/logout', { method: 'POST' }),

  config: () =>
    fetchAPI<{
      has_garmin_credentials: boolean
      has_gemini_key: boolean
      has_saved_tokens: boolean
    }>('/auth/config'),

  // Try to restore session using saved tokens
  restore: () =>
    fetchAPI<{ success: boolean; user: any; message: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ use_saved_tokens: true }),
    }),
}

// Activities API
export const activitiesAPI = {
  getRecent: (limit = 20) =>
    fetchAPI<{ activities: any[]; total: number }>(
      `/activities/recent?limit=${limit}`
    ),

  getByDateRange: (startDate: string, endDate?: string) =>
    fetchAPI<{ activities: any[]; total: number }>(
      `/activities/date-range?start_date=${startDate}${endDate ? `&end_date=${endDate}` : ''}`
    ),

  getStats: (days = 30) =>
    fetchAPI<{
      total_activities: number
      total_duration_hours: number
      total_distance_km: number
      total_calories: number
      activity_types: Record<string, number>
    }>(`/activities/stats?days=${days}`),

  getDetail: (id: string) => fetchAPI<any>(`/activities/${id}`),

  // Detailed activity data
  getSplits: (id: string) => fetchAPI<any>(`/activities/${id}/splits`),

  getHRZones: (id: string) => fetchAPI<any>(`/activities/${id}/hr-zones`),

  getWeather: (id: string) => fetchAPI<any>(`/activities/${id}/weather`),

  getExerciseSets: (id: string) => fetchAPI<any>(`/activities/${id}/exercise-sets`),

  getGear: (id: string) => fetchAPI<any>(`/activities/${id}/gear`),

  // Get all details in one call (comprehensive)
  getFullDetails: (id: string) =>
    fetchAPI<{
      activity_id: string
      activity: any
      splits: any
      typed_splits: any
      split_summaries: any
      hr_zones: any
      weather: any
      exercise_sets: any
      gear: any
      metrics: {
        has_stress: boolean
        has_respiration: boolean
        has_performance_condition: boolean
        has_pace: boolean
        has_cadence: boolean
        has_power: boolean
        has_stride_length: boolean
        has_stamina: boolean
      }
      summary: {
        name: string
        type: string
        duration_seconds: number
        distance_meters: number
        calories: number
        avg_hr: number | null
        max_hr: number | null
        avg_speed: number | null
        max_speed: number | null
        elevation_gain: number | null
        elevation_loss: number | null
        avg_cadence: number | null
        max_cadence: number | null
        avg_stride_length: number | null
        performance_condition: number | null
        training_effect_aerobic: number | null
        training_effect_anaerobic: number | null
        avg_respiration: number | null
        max_respiration: number | null
        avg_stress: number | null
        max_stress: number | null
        vo2max: number | null
        avg_power: number | null
        max_power: number | null
        normalized_power: number | null
        training_load: number | null
        recovery_time: number | null
        start_time: string | null
      }
    }>(`/activities/${id}/full`),

  // Get detailed metrics for chart display
  getMetrics: (id: string) =>
    fetchAPI<{
      activity_id: string
      summary: any
      available_metrics: {
        has_stress: boolean
        has_respiration: boolean
        has_performance_condition: boolean
        has_pace: boolean
        has_cadence: boolean
        has_power: boolean
      }
      weather: any
      hr_zones: any
      splits: Array<{
        lap_number: number
        duration_seconds: number | null
        distance_meters: number | null
        avg_hr: number | null
        max_hr: number | null
        avg_speed: number | null
        avg_cadence: number | null
        elevation_gain: number | null
        avg_respiration: number | null
        avg_stress: number | null
        pace_min_km: string | null
      }>
      charts: {
        has_data: boolean
        heart_rate: Array<{ lap: number; value: number; max?: number }>
        pace: Array<{ lap: number; value: string; speed_ms: number }>
        cadence: Array<{ lap: number; value: number }>
        stress: Array<{ lap: number; value: number }>
        respiration: Array<{ lap: number; value: number }>
        elevation: Array<{ lap: number; value: number }>
        power: Array<{ lap: number; value: number }>
      }
    }>(`/activities/${id}/metrics`),

  // Get typed splits
  getTypedSplits: (id: string) => fetchAPI<any>(`/activities/${id}/typed-splits`),

  // Get split summaries
  getSplitSummaries: (id: string) => fetchAPI<any>(`/activities/${id}/split-summaries`),
}

// Health API
export const healthAPI = {
  getDailyStats: (days = 14) =>
    fetchAPI<{ stats: any[]; total: number }>(`/health/daily-stats?days=${days}`),

  getSummary: (days = 7) =>
    fetchAPI<{
      avg_steps: number
      total_steps: number
      avg_resting_hr: number | null
      avg_stress: number | null
      total_active_minutes: number
      total_calories: number
      avg_sleep_hours: number
      avg_sleep_score: number | null
    }>(`/health/summary?days=${days}`),

  getSleep: (days = 14) =>
    fetchAPI<{ sleep: any[]; total: number }>(`/health/sleep?days=${days}`),

  getHeartRate: (date: string) =>
    fetchAPI<any>(`/health/heart-rate/${date}`),

  getBodyBattery: () => fetchAPI<any>('/health/body-battery'),

  getBodyBatteryDetailed: (date?: string) =>
    fetchAPI<any>(date ? `/health/body-battery/detailed?bb_date=${date}` : '/health/body-battery/detailed'),

  getTrainingReadiness: () => fetchAPI<any>('/health/training-readiness'),

  // Comprehensive health snapshot
  getFullSnapshot: (date?: string) =>
    fetchAPI<any>(date ? `/health/full-snapshot?snapshot_date=${date}` : '/health/full-snapshot'),

  // Performance metrics (VO2max, race predictions, etc.)
  getPerformanceMetrics: () =>
    fetchAPI<{
      race_predictions: any
      endurance_score: any
      hill_score: any
      max_metrics: any
      fitness_age: any
      lactate_threshold: any
      personal_records: any
      hr_zones: any
    }>('/health/performance-metrics'),

  getRespiration: (date: string) => fetchAPI<any>(`/health/respiration/${date}`),

  getStress: (date: string) => fetchAPI<any>(`/health/stress/${date}`),

  getAllDayStress: (date: string) => fetchAPI<any>(`/health/stress/${date}/all-day`),

  getSpo2: (date: string) => fetchAPI<any>(`/health/spo2/${date}`),

  getHydration: (date: string) => fetchAPI<any>(`/health/hydration/${date}`),

  getIntensityMinutes: (weeks = 4) =>
    fetchAPI<any[]>(`/health/intensity-minutes?weeks=${weeks}`),

  getHRV: (date: string) => fetchAPI<any>(`/health/hrv/${date}`),

  getDevices: () =>
    fetchAPI<{ devices: any[]; primary_device: any }>('/health/devices'),

  getGarminGoals: () => fetchAPI<any>('/health/goals'),

  getBadges: () => fetchAPI<any[]>('/health/badges'),

  getPersonalRecords: () => fetchAPI<any>('/health/personal-records'),

  // Sync endpoints
  getSyncStatus: () =>
    fetchAPI<{
      sync_status: Record<string, {
        last_sync_at: string | null
        last_sync_success: boolean
        records_synced: number
        is_stale: boolean
      }>
      server_time: string
    }>('/health/sync/status'),

  syncData: () =>
    fetchAPI<{
      success: boolean
      results: Record<string, {
        success: boolean
        count: number
        error: string | null
      }>
      total_time_seconds: number
      synced_at: string
    }>('/health/sync', { method: 'POST' }),
}

// AI API
export const aiAPI = {
  chat: (message: string, sessionId?: string) =>
    fetchAPI<{ response: string; session_id: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId }),
    }),

  generateWorkout: (data: {
    scheduled_type: string
    vdot_score?: number
    training_phase?: string
    primary_goal?: string
    user_rpe?: number
  }) =>
    fetchAPI<any>('/ai/generate-workout', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  generateWeekPlan: (data: { 
    primary_goal: string
    training_phase?: string
    supplementary_activities?: string[]
    supplementary_frequency?: Record<string, number>  // e.g., { wim_hof: 7, yoga: 3 }
    goal_time?: string  // e.g., "45:00" for 10K, "1:45:00" for half
    goal_distance_km?: number
    target_vdot?: number
  }) =>
    fetchAPI<any>('/ai/generate-week-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  generateMonthPlan: (data: { 
    primary_goal: string
    training_phase?: string
    target_race_date?: string
    supplementary_activities?: string[]
    supplementary_frequency?: Record<string, number>  // e.g., { wim_hof: 7, yoga: 3 }
    goal_time?: string
    goal_distance_km?: number
    target_vdot?: number
  }) =>
    fetchAPI<any>('/ai/generate-month-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  generateInsights: (period = 'week') =>
    fetchAPI<any>('/ai/generate-insights', {
      method: 'POST',
      body: JSON.stringify({ period }),
    }),

  recommendGoals: () => fetchAPI<any>('/ai/recommend-goals'),

  analyzeActivity: (activityId: string, regenerate: boolean = false) =>
    fetchAPI<{
      activity_id: string
      analysis: {
        overall_rating: string
        overall_score: number
        one_liner: string
        performance_summary: string
        comparison_to_history: {
          trend: string
          pace_vs_avg: string
          pace_diff_percent: number | null
          hr_vs_avg: string
          hr_diff_bpm: number | null
          efficiency_trend: string
          notable_change: string
        }
        what_went_well: Array<{
          category: string
          observation: string
          metric: string
          significance: string
        }>
        what_needs_improvement: Array<{
          category: string
          observation: string
          metric: string
          recommendation: string
        }>
        heart_rate_analysis: {
          zone_assessment: string
          efficiency: string
          recommendations: string[]
        }
        pace_analysis: {
          consistency: string
          pacing_strategy: string
          recommendations: string[]
        }
        training_effect_assessment: {
          aerobic_rating: string
          aerobic_insight: string
          anaerobic_rating: string
          anaerobic_insight: string
        }
        stress_analysis?: {
          avg_stress: number | null
          max_stress: number | null
          stress_during_activity: string
          stress_management: string
          insight: string
        }
        respiration_analysis?: {
          avg_respiration: number | null
          max_respiration: number | null
          breathing_efficiency: string
          insight: string
        }
        performance_condition_analysis?: {
          value: number | null
          interpretation: string
          insight: string
        }
        power_analysis?: {
          avg_power: number | null
          normalized_power: number | null
          power_efficiency: string
          insight: string
        }
        key_takeaways: string[]
        recommendations_for_next_time: Array<{
          priority: string
          action: string
          expected_benefit: string
        }>
        recovery_suggestion: string
        generated_at: string
        ai_model: string
      }
      activity_summary: {
        name: string
        type: string
        duration_minutes: number
        distance_km: number
        calories: number
        avg_hr: number
        max_hr: number
        training_effect_aerobic: number
        training_effect_anaerobic: number
        elevation_gain: number
        avg_cadence: number
        start_time: string
        avg_stress: number | null
        max_stress: number | null
        avg_respiration: number | null
        max_respiration: number | null
        performance_condition: number | null
        avg_stride_length: number | null
        avg_power: number | null
        max_power: number | null
        normalized_power: number | null
        training_load: number | null
        recovery_time_minutes: number | null
        vo2_max: number | null
      }
      comparison_activities_count: number
      has_splits: boolean
      has_weather: boolean
      cached: boolean
      cached_at?: string
    }>(`/ai/activity/${activityId}/analysis${regenerate ? '?regenerate=true' : ''}`),

  // Workout plan pinning and tracking
  pinPlan: (data: { plan_type: string; plan_data: any; start_date?: string }) =>
    fetchAPI<{ success: boolean; plan_id: number; message: string }>('/ai/pin-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPinnedPlans: () =>
    fetchAPI<{ plans: any[] }>('/ai/pinned-plans'),

  getPinnedPlanDetails: (planId: number) =>
    fetchAPI<any>(`/ai/pinned-plan/${planId}`),

  deletePinnedPlan: (planId: number) =>
    fetchAPI<{ success: boolean }>(`/ai/pinned-plan/${planId}`, {
      method: 'DELETE',
    }),

  adjustPinnedPlan: (data: { plan_id: number; adjustment_type?: string }) =>
    fetchAPI<{
      success: boolean
      message: string
      adjustments_made: number
      adjustment_factor: number
      adjustments: string[]
      readiness_data: {
        body_battery: number
        sleep_score: number
        hrv_status: string
        readiness_score: number
      }
    }>('/ai/adjust-pinned-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Activity matching
  matchActivity: (data: { scheduled_workout_id: number; activity_id: string }) =>
    fetchAPI<{ success: boolean; message: string }>('/ai/match-activity', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  autoMatchActivities: () =>
    fetchAPI<{ success: boolean; matched_count: number; matched_workouts: any[] }>(
      '/ai/auto-match-activities',
      { method: 'POST' }
    ),

  // Readiness and HR zones
  getTodayReadiness: () =>
    fetchAPI<{
      date: string
      body_battery: number | null
      sleep_score: number | null
      hrv_status: string
      hrv_avg: number | null
      hrv_weekly_avg: number | null
      resting_hr: number | null
      stress_level: number | null
      readiness_score: number
      should_rest: boolean
      should_reduce_intensity: boolean
      adjustment_reason: string | null
    }>('/ai/today-readiness'),

  getHRZones: () =>
    fetchAPI<{
      max_hr: number
      resting_hr: number
      zones: Record<string, { name: string; min_bpm: number; max_bpm: number }>
      source: string
    }>('/ai/hr-zones'),
}

// Workouts API
export const workoutsAPI = {
  getPlans: () => fetchAPI<{ plans: any[]; total: number }>('/workouts/plans'),

  createPlan: (plan: any) =>
    fetchAPI<{ success: boolean; plan_id: number }>('/workouts/plans', {
      method: 'POST',
      body: JSON.stringify(plan),
    }),

  getScheduled: (days = 7) =>
    fetchAPI<{ workouts: any[]; total: number }>(
      `/workouts/scheduled?days=${days}`
    ),

  completeWorkout: (id: number, data: any) =>
    fetchAPI<{ success: boolean }>(`/workouts/scheduled/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getGoals: () => fetchAPI<{ goals: any[]; total: number }>('/workouts/goals'),

  createGoal: (goal: any) =>
    fetchAPI<{ success: boolean; goal_id: number }>('/workouts/goals', {
      method: 'POST',
      body: JSON.stringify(goal),
    }),

  // Send single workout to Garmin with proper structure (warmup, main, cooldown)
  sendToGarmin: (workout: {
    title: string
    description: string
    type: string
    duration_minutes: number
    steps?: Array<{
      type: string // warmup, active, recovery, rest, cooldown, repeat
      duration_minutes?: number
      duration_type?: string // time, distance, open
      distance_meters?: number
      target_type?: string // pace, heart_rate, open
      target_pace_min?: string // e.g., "5:30"
      target_pace_max?: string
      target_hr_zone?: number // 1-5
      target_hr_bpm_low?: number
      target_hr_bpm_high?: number
      description?: string
      repeat_count?: number
      repeat_steps?: any[]
    }>
    target_hr_zone?: string
    scheduled_date?: string
  }) =>
    fetchAPI<{
      success: boolean
      message: string
      workout_id?: string
      scheduled_id?: string
      workout_data: any
      manual_creation_url: string
      steps_summary?: Array<{
        type: string
        duration: string
        target: string
      }>
    }>('/workouts/send-to-garmin', {
      method: 'POST',
      body: JSON.stringify(workout),
    }),

  // Send a day's workouts to Garmin
  sendDayToGarmin: (workouts: Array<{
    title: string
    description: string
    type: string
    duration_minutes: number
    steps?: any[]
    scheduled_date?: string
  }>) =>
    fetchAPI<{
      success: boolean
      message: string
      results: Array<{
        title: string
        success: boolean
        workout_id?: string
        error?: string
      }>
    }>('/workouts/send-day-to-garmin', {
      method: 'POST',
      body: JSON.stringify(workouts),
    }),

  // Send a week's workouts to Garmin
  sendWeekToGarmin: (data: {
    workouts: Array<{
      title: string
      description: string
      type: string
      duration_minutes: number
      steps?: any[]
      scheduled_date?: string
    }>
    plan_name?: string
  }) =>
    fetchAPI<{
      success: boolean
      message: string
      plan_name?: string
      results: Array<{
        title: string
        date?: string
        success: boolean
        workout_id?: string
        error?: string
      }>
      manual_url: string
    }>('/workouts/send-week-to-garmin', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Send a month's workouts to Garmin
  sendMonthToGarmin: (data: {
    workouts: Array<{
      title: string
      description: string
      type: string
      duration_minutes: number
      steps?: any[]
      scheduled_date?: string
    }>
    plan_name?: string
  }) =>
    fetchAPI<{
      success: boolean
      message: string
      plan_name?: string
      results: Array<{
        title: string
        date?: string
        success: boolean
        workout_id?: string
        error?: string
      }>
      manual_url: string
    }>('/workouts/send-month-to-garmin', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Adjust plan based on readiness
  adjustPlan: (data: {
    plan_data: any
    body_battery: number
    sleep_score?: number
    resting_hr?: number
    stress_level?: number
    recent_training_load?: number
  }) =>
    fetchAPI<{
      success: boolean
      adjusted_plan: any
      adjustments_made: string[]
      adjustment_factor: number
    }>('/workouts/adjust-plan', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
