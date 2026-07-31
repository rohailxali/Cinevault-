export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-bg-elevated rounded-md ${className}`}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="flex-none w-[140px] sm:w-[180px] md:w-[220px] aspect-[2/3] relative rounded-md overflow-hidden">
      <Skeleton className="w-full h-full" />
    </div>
  );
}

export function RowSkeleton() {
  return (
    <div className="flex gap-4 overflow-hidden px-12 py-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
