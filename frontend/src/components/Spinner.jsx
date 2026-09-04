export default function Spinner({ message = 'Processing...' }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="card flex flex-col items-center gap-4 py-8 px-10 animate-slide-up">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border-2 border-surface-border" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin" />
        </div>
        <p className="text-sm text-gray-400 font-medium">{message}</p>
      </div>
    </div>
  )
}
