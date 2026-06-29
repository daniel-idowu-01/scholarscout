export default function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-7 h-7', lg: 'w-10 h-10' }
  return (
    <div
      className={`${sizes[size]} animate-spin rounded-none`}
      style={{
        border: '2px solid var(--border)',
        borderTopColor: '#d4a853',
      }}
    />
  )
}