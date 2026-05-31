import { Cpu, Server, Sparkles } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="mt-10 border-t hairline pt-5 pb-2">
      <div className="flex flex-col gap-2 text-[11px] text-slate-500 sm:flex-row sm:items-center sm:justify-center sm:gap-6">
        <span className="inline-flex items-center gap-1.5">
          <Cpu size={13} className="text-teal-accent" /> Control plane decides
        </span>
        <span className="hidden sm:inline text-slate-700">·</span>
        <span className="inline-flex items-center gap-1.5">
          <Server size={13} className="text-cyan-accent" /> Execution plane deploys
        </span>
        <span className="hidden sm:inline text-slate-700">·</span>
        <span className="inline-flex items-center gap-1.5">
          <Sparkles size={13} className="text-amber-300" /> AI enriches, never touches keys or servers
        </span>
      </div>
    </footer>
  );
}
