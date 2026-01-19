import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface SleepChartProps {
  data: Array<{
    date: string
    total_hours: number
    deep_hours: number
    light_hours: number
    rem_hours: number
  }>
}

export default function SleepChart({ data }: SleepChartProps) {
  const chartData = data
    .slice()
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      deep: parseFloat(d.deep_hours.toFixed(1)),
      light: parseFloat(d.light_hours.toFixed(1)),
      rem: parseFloat(d.rem_hours.toFixed(1)),
    }))

  if (chartData.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted-foreground">
        No sleep data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="#666"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#666"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${value}h`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a2e',
            border: '1px solid #333',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#888' }}
          formatter={(value: number) => [`${value}h`]}
        />
        <Legend
          wrapperStyle={{ paddingTop: '20px' }}
          formatter={(value) => (
            <span style={{ color: '#888', textTransform: 'capitalize' }}>
              {value}
            </span>
          )}
        />
        <Bar dataKey="deep" name="Deep" stackId="sleep" fill="#8b5cf6" radius={[0, 0, 0, 0]} />
        <Bar dataKey="light" name="Light" stackId="sleep" fill="#6366f1" radius={[0, 0, 0, 0]} />
        <Bar dataKey="rem" name="REM" stackId="sleep" fill="#22c55e" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
