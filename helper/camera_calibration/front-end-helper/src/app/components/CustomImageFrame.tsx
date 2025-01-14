import Image from "next/image";
import { IoCloseCircle } from "react-icons/io5";

interface CustomImageFrameProps {
  src: string;
  alt: string;
  onRemove?: () => void;
  className?: string;
}

export default function RemovableImageFrame({
  src,
  alt,
  onRemove,
  className = "",
}: CustomImageFrameProps) {
  return (
    <div className={`relative w-full h-full ${className}`}>
      {/* Frame container */}
      <div className="w-full h-full border-2 border-gray-300 rounded-lg overflow-hidden relative">
        {/* Image */}
        <Image
          src={src}
          alt={alt}
          fill
          style={{ objectFit: "contain" }}
          className="p-2"
        />

        {/* Remove button */}
        {onRemove && (
          <button
            onClick={onRemove}
            className="absolute top-2 right-2 z-10 text-red-500 hover:text-red-600 transition-colors"
            aria-label="Remove image"
          >
            <IoCloseCircle size={24} />
          </button>
        )}
      </div>
    </div>
  );
}
