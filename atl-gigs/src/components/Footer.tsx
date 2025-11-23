import { Music } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-12 sm:mt-20 border-t border-white/5 pt-6 pb-8 sm:pt-8 sm:pb-12 text-center">
      <div className="flex items-center justify-center gap-2 mb-4">
        <div className="w-8 h-8 bg-gradient-to-br from-neutral-800 to-neutral-900 rounded-lg flex items-center justify-center">
          <Music size={16} className="text-neutral-400" />
        </div>
        <span className="font-bold text-neutral-300">
          ATL<span className="text-neutral-600">Gigs</span>
        </span>
      </div>
      <p className="text-neutral-600 text-sm">
        Aggregating Atlanta's live music scene. Made with care in ATL.
      </p>
    </footer>
  );
}
