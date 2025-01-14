"use client";

export function StandardButton({
  text,
  onClick,
  className,
}: {
  text: string;
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      className={`
        w-full
        relative
        bg-gray-800 
        text-white 
        font-medium 
        py-2 
        px-4 
        rounded-lg 
        shadow-lg
        overflow-hidden
        transform
        transition-all
        duration-300
        ease-in-out
        hover:scale-105
        hover:bg-gray-700
        hover:shadow-xl
        active:scale-95
        focus:outline-none 
        focus:ring-2 
        focus:ring-gray-500 
        focus:ring-opacity-50
        before:absolute
        before:content-['']
        before:top-0
        before:left-0
        before:w-full
        before:h-full
        before:bg-white
        before:opacity-0
        before:transition-opacity
        before:duration-300
        hover:before:opacity-10
        after:absolute
        after:content-['']
        after:top-0
        after:left-[-100%]
        after:w-full
        after:h-full
        after:bg-gradient-to-r
        after:from-transparent
        after:via-white
        after:to-transparent
        after:opacity-20
        hover:after:animate-shine
        ${className}
      `}
      onClick={onClick}
      style={{
        WebkitTapHighlightColor: "transparent",
      }}
    >
      <span className="relative z-10 inline-flex items-center transition-transform duration-300 group-hover:scale-105">
        {text}
      </span>
      <style jsx>{`
        @keyframes shine {
          0% {
            left: -100%;
          }
          100% {
            left: 100%;
          }
        }
        .hover\\:after\\:animate-shine:hover::after {
          animation: shine 1s ease-in-out;
        }
      `}</style>
    </button>
  );
}
