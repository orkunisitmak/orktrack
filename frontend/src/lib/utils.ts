import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num)
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${Math.round(minutes)} min`
  }
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

export function formatDistance(km: number): string {
  if (km < 1) {
    return `${Math.round(km * 1000)}m`
  }
  return `${km.toFixed(2)} km`
}

export function formatPace(speedKmh: number): string {
  if (speedKmh <= 0) return '--:--'
  const paceMinutes = 60 / speedKmh
  const mins = Math.floor(paceMinutes)
  const secs = Math.round((paceMinutes - mins) * 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function getActivityIcon(type: string): string {
  const icons: Record<string, string> = {
    running: '🏃',
    cycling: '🚴',
    swimming: '🏊',
    walking: '🚶',
    hiking: '🥾',
    strength_training: '💪',
    yoga: '🧘',
    treadmill_running: '🏃',
    indoor_cycling: '🚴',
    other: '🏋️',
  }
  return icons[type] || '🏋️'
}

export function getScoreColor(score: number): string {
  if (score >= 70) return 'text-green-500'
  if (score >= 50) return 'text-yellow-500'
  return 'text-red-500'
}

export function getScoreBgColor(score: number): string {
  if (score >= 70) return 'bg-green-500/20'
  if (score >= 50) return 'bg-yellow-500/20'
  return 'bg-red-500/20'
}
