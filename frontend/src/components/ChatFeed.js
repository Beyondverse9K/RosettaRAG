import React, { useRef, useEffect } from 'react';
import { Database, Cpu, Code, Scan, FileText, ShieldAlert, X, Network, Split, Share2, Sparkles, CircleDashed } from 'lucide-react';
import rosettaBg from '../assets/Rosetta-Background2.jpg';
import WorkflowVisualizer from './WorkflowVisualizer';

export default function ChatFeed({ messages, loading }) {
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const getDatasourceBadge = (source) => {
        if (!source) return null;

        // Custom Composite Icons for Badges
        const config = {
            relational_db: {
                icon: (
                    <div className="relative w-4 h-4 flex items-center justify-center mr-1">
                        <Database className="absolute text-blue-400/40 w-4 h-4" />
                        <Code className="absolute text-blue-400 w-2 h-2" strokeWidth={3} />
                    </div>
                ),
                text: 'Neon PostgreSQL',
                color: 'text-blue-400 border-blue-400/30 bg-blue-400/10'
            },
            graph_db: {
                icon: (
                    <div className="relative w-4 h-4 flex items-center justify-center mr-1">
                        <Network className="absolute text-orange-400/40 w-4 h-4" />
                        <Share2 className="absolute text-orange-400 w-2 h-2 rotate-90" strokeWidth={2.5} />
                    </div>
                ),
                text: 'Neo4j Graph',
                color: 'text-orange-400 border-orange-400/30 bg-orange-400/10'
            },
            vector_db: {
                icon: (
                    <div className="relative w-4 h-4 flex items-center justify-center mr-1">
                        <Scan className="absolute text-emerald-400/40 w-4 h-4" />
                        <FileText className="absolute text-emerald-400 w-2 h-2" strokeWidth={2.5} />
                    </div>
                ),
                text: 'Pinecone Vector',
                color: 'text-emerald-400 border-emerald-400/30 bg-emerald-400/10'
            },
            reject: {
                icon: (
                    <div className="relative w-4 h-4 flex items-center justify-center mr-1">
                        <ShieldAlert className="absolute text-rose-400/40 w-4 h-4 animate-pulse" />
                        <X className="absolute text-rose-400 w-2 h-2" strokeWidth={3} />
                    </div>
                ),
                text: 'Guardrail Intercept',
                color: 'text-rose-400 border-rose-400/30 bg-rose-400/10'
            }
        };

        const style = config[source] || {
            icon: (
                <div className="relative w-4 h-4 flex items-center justify-center mr-1">
                    <Split className="absolute text-purple-400/40 w-4 h-4 -rotate-90" />
                    <Cpu className="absolute text-purple-400 w-2 h-2 animate-pulse" strokeWidth={2.5} />
                </div>
            ),
            text: 'Routing Engine',
            color: 'text-purple-400 border-purple-400/30 bg-purple-400/10'
        };

        return (
            <div className={`flex items-center px-2.5 py-1 mt-4 text-[11px] uppercase tracking-wider font-semibold border rounded-full w-max ${style.color}`}>
                {style.icon}
                <span>Source: {style.text}</span>
            </div>
        );
    };

    return (
        <main className="flex-1 overflow-y-auto relative scroll-smooth px-4 py-8 pb-40">

            <div className="relative z-10 max-w-6xl mx-auto space-y-10">

                {/* The Contained Empty State */}
                {messages.length === 0 && !loading && (
                    <div className="flex flex-col items-center justify-center mt-12 animate-in fade-in duration-1000">

                        <div className="relative w-full h-[600px] mb-2 pointer-events-none">
                            {/* The Base Image */}
                            <div
                                className="absolute inset-0 bg-contain bg-center bg-no-repeat opacity-60 mix-blend-lighten"
                                style={{ backgroundImage: `url(${rosettaBg})` }}
                            ></div>

                            {/* Ultra-subtle edge feathering (24px to 32px thick) */}
                            <div className="absolute top-0 inset-x-0 h-6 bg-gradient-to-b from-[#0B0F19] to-transparent"></div>
                            <div className="absolute bottom-0 inset-x-0 h-8 bg-gradient-to-t from-[#0B0F19] to-transparent"></div>
                            <div className="absolute left-0 inset-y-0 w-6 bg-gradient-to-r from-[#0B0F19] to-transparent"></div>
                            <div className="absolute right-0 inset-y-0 w-6 bg-gradient-to-l from-[#0B0F19] to-transparent"></div>
                        </div>

                        {/* The Greeting Text */}
                        <h2 className="text-xl font-medium text-cyan-200/80 tracking-wide relative z-10">
                            How can I help you today?
                        </h2>
                    </div>
                )}

                {/* Message Feed */}
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

                        {/* User Message */}
                        {msg.role === 'user' ? (
                            <div className="bg-slate-800/80 backdrop-blur-sm border border-white/10 text-slate-100 px-6 py-4 rounded-3xl rounded-tr-sm max-w-[80%] shadow-lg text-[15px] leading-relaxed">
                                {msg.content}
                            </div>
                        ) : (

                            /* Bot Message */
                            <div className="flex gap-5 w-full animate-in fade-in duration-300">
                                <div className="relative shrink-0 w-8 h-8 mt-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shadow-[0_0_10px_rgba(6,182,212,0.15)] overflow-hidden">
                                    <CircleDashed className="absolute text-cyan-400/40 w-7 h-7 animate-[spin_4s_linear_infinite]" strokeWidth={1} />
                                    <Sparkles size={14} className="absolute text-cyan-300 z-10 animate-pulse" />
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="text-slate-200 text-[15px] leading-8 whitespace-pre-wrap">
                                        {msg.content}
                                    </div>
                                    {getDatasourceBadge(msg.datasource)}
                                </div>
                            </div>
                        )}
                    </div>
                ))}

                <WorkflowVisualizer loading={loading} />
                <div ref={messagesEndRef} className="h-4" />
            </div>
        </main>
    );
}