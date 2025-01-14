import Link from "next/link";
import { FaHome } from "react-icons/fa";

export function GoHome({ url }: { url: string }) {
  return (
    <Link
      href={url}
      className="text-2xl w-20 h-20 block
        hover:scale-110 transition-transform duration-200 
        hover:opacity-80 cursor-pointer"
      aria-label="Go to home page"
    >
      <FaHome className="w-full h-full" />
    </Link>
  );
}
