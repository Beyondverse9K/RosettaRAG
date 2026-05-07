import React from 'react';
import { Database, RefreshCw, Cpu, Code, Scan, FileText, Network, Split, Share2 } from 'lucide-react';
import { ReactComponent as RosettaLogo } from '../assets/rosetta-logo.svg';

export default function Sidebar() {
    return (
        <div className="w-64 glass-panel p-6 hidden md:flex flex-col border-r border-white/5 z-10">

            <h2 className="text-2xl font-medium text-white mb-10 flex items-center gap-4">
                <div className="relative w-14 h-14 bg-cyan-500/10 rounded-xl border border-cyan-500/20 shadow-[0_0_15px_rgba(6,182,212,0.15)] flex items-center justify-center">
                    <RefreshCw className="absolute text-cyan-400/60 w-9 h-9 animate-[spin_4s_linear_infinite]" strokeWidth={1.5} />
                    <RosettaLogo className="absolute text-cyan-300 w-6 h-6 z-10" />
                </div>
                Rosetta
            </h2>

            <div className="flex-1 mt-4">
                <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-6">Architecture</h3>
                <ul className="space-y-6 text-sm text-slate-300 font-medium tracking-wide">

                    <li className="flex items-center gap-4">
                        <div className="relative w-8 h-8 flex items-center justify-center">
                            <Split className="absolute text-purple-500/30 w-8 h-8 -rotate-90" strokeWidth={2} />
                            <Cpu className="absolute text-purple-400 w-4 h-4" strokeWidth={2.5} />
                        </div>
                        Polyglot Routing
                    </li>

                    <li className="flex items-center gap-4">
                        <div className="relative w-8 h-8 flex items-center justify-center">
                            <Database className="absolute text-blue-500/30 w-8 h-8" strokeWidth={2} />
                            <Code className="absolute text-blue-400 w-4 h-4" strokeWidth={3} />
                        </div>
                        Text-to-SQL
                    </li>


                    <li className="flex items-center gap-4">
                        <div className="relative w-8 h-8 flex items-center justify-center">
                            <Network className="absolute text-orange-500/30 w-8 h-8" strokeWidth={2} />
                            <Share2 className="absolute text-orange-400 w-4 h-4 rotate-90" strokeWidth={2.5} />
                        </div>
                        Text-to-Cypher
                    </li>

                    <li className="flex items-center gap-4">
                        <div className="relative w-8 h-8 flex items-center justify-center">
                            <Scan className="absolute text-emerald-500/30 w-8 h-8" strokeWidth={2} />
                            <FileText className="absolute text-emerald-400 w-4 h-4" strokeWidth={2.5} />
                        </div>
                        Vector / HyDE
                    </li>

                    <li className="flex items-center gap-4">
                        <div className="relative w-8 h-8 flex items-center justify-center">
                            <RefreshCw className="absolute text-rose-500/30 w-8 h-8 animate-[spin_4s_linear_infinite]" strokeWidth={2} />
                            <RosettaLogo className="absolute text-rose-400 w-4 h-4 z-10" />
                        </div>
                        Self-RAG & CRAG
                    </li>

                </ul>
            </div>
        </div>
    );
}