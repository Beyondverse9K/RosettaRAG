import React from 'react';
import { Send } from 'lucide-react';

export default function FloatingInput({ input, setInput, handleSend, loading }) {
    return (
        <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#0B0F19] via-[#0B0F19]/90 to-transparent pt-12 pb-8 px-4 z-30">
            <div className="max-w-3xl mx-auto relative">
                <div className="glass-input rounded-2xl flex items-end p-2">
          <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                  }
              }}
              className="flex-1 bg-transparent border-none px-4 py-3 text-slate-200 focus:outline-none focus:ring-0 resize-none max-h-32 min-h-[44px] placeholder:text-slate-500"
              placeholder="Ask Rosetta about corporate data..."
              disabled={loading}
              rows={1}
          />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        className="shrink-0 m-1 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:text-slate-500 text-white p-2.5 rounded-xl transition-all flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.3)] disabled:shadow-none"
                    >
                        <Send size={18} />
                    </button>
                </div>
                <div className="text-center mt-3">
          <span className="text-[10px] text-slate-600 font-medium tracking-wide uppercase">
            Rosetta can make mistakes. Verify critical corporate data.
          </span>
                </div>
            </div>
        </div>
    );
}