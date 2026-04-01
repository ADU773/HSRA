import React from 'react';

export default function Topbar({ title, subtitle }) {
    return (
        <header className="flex justify-between items-center px-10 py-3 w-full bg-[#f7f9fb] dark:bg-slate-900 border-b border-[#acb3b7]/15 z-40 sticky top-0">
            <div className="flex items-center gap-8">
                <div>
                     <h1 className="text-lg font-bold tracking-tight text-[#2c3437] dark:text-slate-100 font-headline">{title || 'Node Alpha Dashboard'}</h1>
                     {subtitle && <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mt-0.5">{subtitle}</p>}
                </div>
            </div>

            <div className="flex items-center gap-6">
                <div className="relative w-64 hidden md:block">
                    <input 
                        type="text" 
                        placeholder="Search events..." 
                        className="w-full bg-surface-container-low border-none rounded-full py-1.5 px-10 text-sm focus:ring-2 focus:ring-primary/20 outline-none placeholder:text-outline-variant"
                    />
                    <span className="material-symbols-outlined absolute left-3 top-1.5 text-outline text-sm">search</span>
                </div>
                
                <div className="flex items-center gap-4 text-on-surface-variant">
                    <button className="material-symbols-outlined hover:text-primary transition-colors">memory</button>
                    <button className="material-symbols-outlined hover:text-primary transition-colors">cloud_done</button>
                    <div className="relative">
                        <button className="material-symbols-outlined hover:text-primary transition-colors">notifications</button>
                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-error rounded-full outline outline-2 outline-surface-lowest"></span>
                    </div>
                </div>

                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white overflow-hidden border-2 border-primary-container font-headline font-bold text-xs">
                    AD
                </div>
            </div>
        </header>
    );
}
