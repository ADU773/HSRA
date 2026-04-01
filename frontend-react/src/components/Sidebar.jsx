import React from 'react';

export default function Sidebar({ activeView, setActiveView }) {
    const navItems = [
        { id: 'dashboard',   icon: 'dashboard',  label: 'Overview' },
        { id: 'analysis',    icon: 'analytics',  label: 'Analysis' },
        { id: 'data_center', icon: 'database',   label: 'Data Center' },
        // Decorative extra tabs to match Stitch UI:
        { id: 'reports',     icon: 'assessment', label: 'Reports' },
        { id: 'settings',    icon: 'settings',   label: 'Settings' }
    ];

    return (
        <aside className="h-screen w-64 fixed left-0 top-0 bg-[#f0f4f7] dark:bg-slate-950 flex flex-col p-6 space-y-8 z-50 transition-all duration-300 ease-in-out">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 primary-gradient rounded-lg flex items-center justify-center">
                    <span className="material-symbols-outlined text-white text-sm">auto_awesome</span>
                </div>
                <span className="text-xl font-black text-[#007B83] font-headline">TrashSense AI</span>
            </div>

            <div className="flex items-center gap-3 p-3 bg-surface-container-high rounded-xl">
                <div className="w-10 h-10 rounded-lg overflow-hidden bg-primary-container flex items-center justify-center">
                     <span className="material-symbols-outlined text-primary">memory</span>
                </div>
                <div>
                    <p className="font-headline font-bold text-sm text-on-surface">Node Alpha</p>
                    <p className="text-[10px] text-on-surface-variant uppercase tracking-widest font-bold flex items-center gap-1.5 mt-0.5">
                        <span className="ai-pulse"></span>
                        Detection Active
                    </p>
                </div>
            </div>

            <nav className="flex-grow space-y-2">
                {navItems.map((item) => {
                    const isActive = activeView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveView(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg shadow-sm transition-all duration-300 ${
                                isActive 
                                    ? "bg-white dark:bg-slate-800 text-[#007B83] font-semibold" 
                                    : "text-[#596064] dark:text-slate-400 hover:text-[#007B83] hover:bg-[#ffffff]/50"
                            }`}
                        >
                            <span className="material-symbols-outlined">{item.icon}</span>
                            <span className="font-['Inter'] text-sm tracking-wide">{item.label}</span>
                        </button>
                    )
                })}
            </nav>

            <button className="w-full py-3 px-4 bg-gradient-to-br from-primary to-primary-dim text-white rounded-xl font-headline font-bold text-sm shadow-md hover:scale-95 transition-transform duration-200">
                Export Analysis
            </button>

            <div className="pt-6 border-t border-outline-variant/15 space-y-2">
                <button className="w-full flex items-center gap-3 px-4 py-2 text-[#596064] dark:text-slate-400 hover:text-[#007B83] transition-colors">
                    <span className="material-symbols-outlined">help</span>
                    <span className="text-xs font-['Inter']">Support</span>
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2 text-[#596064] dark:text-slate-400 hover:text-[#007B83] transition-colors">
                    <span className="material-symbols-outlined">description</span>
                    <span className="text-xs font-['Inter']">Documentation</span>
                </button>
            </div>
        </aside>
    );
}
