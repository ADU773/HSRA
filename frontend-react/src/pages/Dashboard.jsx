import React, { useRef, useState } from 'react';
import { fmtBytes } from '../utils';

export default function Dashboard({
    onAnalyze,
    view,
    progress,
    jobId
}) {
    const [file, setFile] = useState(null);
    const [useVlm, setUseVlm] = useState(true);
    const [dragOver, setDragOver] = useState(false);
    const [uploading, setUploading] = useState(false);
    const inputRef = useRef();
    const logRef = useRef();

    const ALLOWED_EXT = ['mp4','avi','mov','mkv','webm','m4v'];

    function handleFile(f) {
        const ext = f.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXT.includes(ext)) {
            alert(`Unsupported file type: .${ext}\nUse MP4, AVI, MOV, MKV or WebM.`);
            return;
        }
        setFile(f);
    }

    function onDrop(e) {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
    }

    async function handleAnalyze() {
        if (!file || uploading) return;
        setUploading(true);
        try { 
            await onAnalyze(file, useVlm);
        } catch (e) { 
            setUploading(false);
        }
    }

    // Determine what to show in the Hero Video Box.
    const isUploading = view === 'progress' && progress.percent < 100 && progress.message.includes("Uploading");
    const isProcessing = view === 'progress' && (!progress.message.includes("Uploading") || progress.percent === 100);

    return (
        <div className="p-10 space-y-8 flex-grow">
            
            {/* Quick Action / VLM Toggle */}
            <div className="flex justify-end mb-4">
                <label className="flex items-center gap-3 cursor-pointer p-3 bg-surface-container-lowest border border-outline-variant/10 rounded-xl shadow-sm hover:bg-surface-container-low transition-colors">
                    <span className="text-sm font-bold text-on-surface">Enable VLMnano Descriptions</span>
                    <div className="relative">
                        <input type="checkbox" className="sr-only" checked={useVlm} onChange={e => setUseVlm(e.target.checked)} />
                        <div className={`block w-10 h-6 rounded-full transition-colors ${useVlm ? 'bg-primary' : 'bg-outline-variant'}`}></div>
                        <div className={`dot absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${useVlm ? 'transform translate-x-4' : ''}`}></div>
                    </div>
                </label>
            </div>

            {/* Hero Grid: Video/Upload + Event Log */}
            <div className="grid grid-cols-12 gap-6">
                
                {/* Visual Area (Upload or Processing) */}
                <div className="col-span-12 lg:col-span-9 bg-surface-container-lowest rounded-[1.5rem] overflow-hidden relative shadow-sm flex flex-col">
                    <div className="aspect-video bg-inverse-surface relative group flex-grow flex items-center justify-center border-[3px] border-transparent transition-all">
                        
                        {view === 'upload' && !file && (
                            <div 
                                className={`absolute inset-0 flex flex-col items-center justify-center cursor-pointer transition-colors ${dragOver ? 'bg-primary/10 border-primary border-[3px] border-dashed rounded-[1.5rem]' : ''}`}
                                onClick={() => inputRef.current.click()}
                                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={onDrop}
                            >
                                <input ref={inputRef} type="file" accept="video/*" hidden onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
                                <div className="w-20 h-20 bg-surface-container flex items-center justify-center rounded-full mb-4">
                                    <span className="material-symbols-outlined text-4xl text-outline">upload_file</span>
                                </div>
                                <p className="font-headline font-bold text-white text-xl">Drag & Drop Video Here</p>
                                <p className="text-outline-variant text-sm mt-2">MP4 · AVI · MOV · MKV</p>
                            </div>
                        )}

                        {view === 'upload' && file && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-inverse-surface">
                                <span className="material-symbols-outlined text-6xl text-primary mb-4">movie</span>
                                <h3 className="text-white font-headline font-bold text-2xl">{file.name}</h3>
                                <p className="text-outline-variant mt-2">{fmtBytes(file.size)}</p>
                                <div className="mt-8 flex gap-4">
                                    <button onClick={handleAnalyze} disabled={uploading} className="px-8 py-3 bg-primary text-on-primary font-bold rounded-xl shadow-lg hover:scale-105 transition-transform">
                                        {uploading ? 'Initializing...' : 'Start Scene Analysis'}
                                    </button>
                                    <button onClick={() => { setFile(null); setUploading(false); }} className="px-8 py-3 bg-surface-container-high text-on-surface font-bold rounded-xl hover:bg-surface-variant transition-colors">
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Processing View — smooth SVG spinner */}
                        {view === 'progress' && (
                            <div className="absolute inset-0 bg-[#0a0e10] flex flex-col items-center justify-center">

                                {/* SVG Ring Spinner */}
                                <div className="relative mb-6" style={{width: 128, height: 128}}>
                                    <svg
                                        width="128" height="128" viewBox="0 0 128 128"
                                        className="absolute inset-0 animate-spin"
                                        style={{animationDuration: '1.8s', animationTimingFunction: 'linear'}}
                                    >
                                        {/* Track ring */}
                                        <circle cx="64" cy="64" r="54" fill="none" stroke="#1c2c30" strokeWidth="8"/>
                                        {/* Animated arc */}
                                        <circle
                                            cx="64" cy="64" r="54"
                                            fill="none"
                                            stroke="#006978"
                                            strokeWidth="8"
                                            strokeLinecap="round"
                                            strokeDasharray="85 254"
                                            strokeDashoffset="0"
                                        />
                                    </svg>
                                    {/* Percentage in centre — outside the spinning SVG so text stays still */}
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <span className="text-white font-headline font-extrabold text-2xl tabular-nums">
                                            {Math.round(progress.percent)}%
                                        </span>
                                    </div>
                                </div>

                                {/* Status text */}
                                <h3 className="text-white font-headline font-bold text-xl mb-3 text-center max-w-xs px-4 leading-snug">
                                    {progress.message || 'Processing…'}
                                </h3>
                                <div className="flex items-center gap-2">
                                    <span className="ai-pulse"></span>
                                    <p className="text-[#8debff] font-mono text-[10px] uppercase tracking-[0.2em]">
                                        {isUploading ? 'Uploading to server' : 'Model engine active'}
                                    </p>
                                </div>

                                {/* Corner badges */}
                                <div className="absolute top-4 left-4 flex gap-2">
                                    <span className="bg-white/5 backdrop-blur-sm border border-white/10 text-white text-[10px] px-3 py-1.5 rounded-full flex items-center gap-2 font-bold tracking-widest">
                                        <span className="ai-pulse"></span>
                                        {isUploading ? 'UPLOADING' : 'ANALYZING'}
                                    </span>
                                    <span className="bg-white/5 backdrop-blur-sm border border-white/10 text-[#8debff] text-[10px] px-3 py-1.5 rounded-full font-bold tracking-widest">
                                        MODEL ENGINE
                                    </span>
                                </div>
                            </div>
                        )}

                    </div>
                    
                    {/* Video Stats Footer */}
                    <div className="px-6 py-4 flex items-center justify-between border-t border-surface-container-high bg-surface-container-low min-h-[72px]">
                        <div className="flex gap-8">
                            <div className="flex flex-col">
                                <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">Active Model</span>
                                <span className="text-sm font-headline font-bold text-primary">best.pt ensemble</span>
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest">System Status</span>
                                <span className="text-sm font-headline font-bold">{view === 'upload' ? 'Awaiting Input' : 'Processing'}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Event Log Section */}
                <div className="col-span-12 lg:col-span-3 bg-surface-container-lowest rounded-[1.5rem] shadow-sm flex flex-col overflow-hidden h-full max-h-[540px]">
                    <div className="p-6 border-b border-surface-container flex justify-between items-center">
                        <h2 className="font-headline font-bold text-sm">Real-time Event Log</h2>
                        <span className="material-symbols-outlined text-on-surface-variant text-sm">tune</span>
                    </div>
                    <div className="flex-grow overflow-y-auto p-4 flex flex-col gap-2" ref={logRef}>
                        {progress && progress.logs && progress.logs.length > 0 ? (
                            [...progress.logs].reverse().map((log, i) => (
                                <div key={i} className="p-3 bg-surface-container-low rounded-xl border-l-4 border-outline/40 hover:bg-surface-container-high transition-colors">
                                    <p className="text-xs text-on-surface leading-snug break-words font-mono">{log}</p>
                                </div>
                            ))
                        ) : (
                            <div className="h-full flex items-center justify-center text-outline-variant text-sm font-medium">
                                No events logged yet.
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Model Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
                {/* best.pt */}
                <div className="bg-surface-container-lowest p-6 rounded-[1.5rem] shadow-sm border-b-4 border-primary/20">
                    <div className="flex justify-between items-start mb-6">
                        <div className="w-10 h-10 bg-primary-container/20 rounded-xl flex items-center justify-center text-primary">
                            <span className="material-symbols-outlined">star</span>
                        </div>
                        <span className="px-3 py-1 bg-secondary-container text-on-secondary-container text-[10px] font-bold rounded-full">STANDBY</span>
                    </div>
                    <h3 className="font-headline font-extrabold text-on-surface mb-1">best.pt</h3>
                    <p className="text-xs text-on-surface-variant mb-4">Master Custom Trash Model</p>
                </div>
                {/* yolo11n.pt */}
                <div className="bg-surface-container-lowest p-6 rounded-[1.5rem] shadow-sm border-b-4 border-tertiary/20">
                    <div className="flex justify-between items-start mb-6">
                        <div className="w-10 h-10 bg-tertiary-container/20 rounded-xl flex items-center justify-center text-tertiary">
                            <span className="material-symbols-outlined">bolt</span>
                        </div>
                        <span className="px-3 py-1 bg-secondary-container text-on-secondary-container text-[10px] font-bold rounded-full">STANDBY</span>
                    </div>
                    <h3 className="font-headline font-extrabold text-on-surface mb-1">yolo11n.pt</h3>
                    <p className="text-xs text-on-surface-variant mb-4">Baseline Object Engine</p>
                </div>
                {/* VLMnano */}
                <div className={`bg-surface-container-lowest p-6 rounded-[1.5rem] shadow-sm border-b-4 ${useVlm ? 'border-error/20' : 'border-outline/20'}`}>
                    <div className="flex justify-between items-start mb-6">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${useVlm ? 'bg-error-container/20 text-error' : 'bg-surface-container text-outline'}`}>
                            <span className="material-symbols-outlined">visibility</span>
                        </div>
                        <span className={`px-3 py-1 text-[10px] font-bold rounded-full ${useVlm ? 'bg-error-container/20 text-error' : 'bg-surface-container text-outline'}`}>
                            {useVlm ? 'ACTIVE' : 'DISABLED'}
                        </span>
                    </div>
                    <h3 className={`font-headline font-extrabold mb-1 ${useVlm ? 'text-on-surface' : 'text-outline'}`}>VLMnano</h3>
                    <p className="text-xs text-on-surface-variant mb-4">Visual Language Model</p>
                </div>
            </div>

        </div>
    );
}
