interface Props {
  className?: string;
}

export function PrismaLogo({ className }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      aria-label="PRISMA Logo"
      role="img"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="prisma-spectrum" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0%" stopColor="#16a34a" />
          <stop offset="25%" stopColor="#2563eb" />
          <stop offset="50%" stopColor="#ea580c" />
          <stop offset="75%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#eab308" />
        </linearGradient>
      </defs>
      <path
        d="M4 20 L12 4 L20 20 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <line
        x1="14"
        y1="13"
        x2="22"
        y2="13"
        stroke="url(#prisma-spectrum)"
        strokeWidth={2}
        strokeLinecap="round"
      />
    </svg>
  );
}
