import React, { useState, useEffect } from 'react';
import { Sparkles, CheckCircle2, CircleDashed, Loader2 } from 'lucide-react';

export default function WorkflowVisualizer({ loading }) {
    const [workflowStep, setWorkflowStep] = useState(0);

    useEffect(() => {
        if (loading) {
            setWorkflowStep(0);
            const timers = [
                setTimeout(() => setWorkflowStep(1), 1200), // Route
                setTimeout(() => setWorkflowStep(2), 3500), // Retrieve
                setTimeout(() => setWorkflowStep(3), 6000), // Grade
            ];
            return () => timers.forEach(clearTimeout);
        }
    }, [loading]);

    if (!loading) return null;

    const steps = [
        { id: 0, label: "Polyglot Router", desc: "Analyzing query intent & selecting database" },
        { id: 1, label: "Knowledge Retrieval", desc: "Executing Cypher/SQL/HyDE searches" },
        { id: 2, label: "CRAG Evaluator", desc: "Grading relevance and filtering context" },
        { id: 3, label: "Report Generator", desc: "Synthesizing finalized grounded response" }
    ];

    return (
        <div className="flex gap-5 w-full animate-in fade-in zoom-in-95 duration-300">
            <div className="shrink-0 w-8 h-8 mt-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                <Sparkles size={16} className="text-cyan-400"/>
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex flex-col gap-3 max-w-md">
                    <h3 className="text-sm font-medium text-cyan-400 mb-2">Analyzing Request</h3>
                    {steps.map((step) => {
                        const isCompleted = workflowStep > step.id;
                        const isActive = workflowStep === step.id;

                        return (
                            <div key={step.id} className={`p-4 rounded-xl border transition-all duration-500 flex gap-4 items-start ${
                                isActive ? 'bg-slate-800/80 border-cyan-500/40 shadow-[0_0_20px_rgba(6,182,212,0.1)]' :
                                    isCompleted ? 'bg-slate-800/30 border-white/5 opacity-70' :
                                        'bg-transparent border-transparent opacity-40'
                            }`}>
                                <div className="mt-0.5">
                                    {isCompleted ? <CheckCircle2 className="text-emerald-400" size={18} /> :
                                        isActive ? <Loader2 className="text-cyan-400 animate-spin" size={18} /> :
                                            <CircleDashed className="text-slate-600" size={18} />}
                                </div>
                                <div>
                                    <h4 className={`text-sm font-semibold tracking-wide ${isActive ? 'text-cyan-100' : 'text-slate-300'}`}>{step.label}</h4>
                                    <p className="text-xs text-slate-500 mt-1.5 leading-snug">{step.desc}</p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}