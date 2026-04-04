import React, { useState, useEffect, useCallback } from 'react';
import { fetchFrameList, frameUrl } from '../api';
import CLIPVerification from '../components/CLIPVerification';

// ── Frame Gallery sub-component ───────────────────────────────────────────────
function FrameGallery({ jobId, throwingEvents, fps }) {
    const [frames,       setFrames]       = useState([]);
    const [activeIdx,    setActiveIdx]    = useState(0);
    const [loading,      setLoading]      = useState(true);
    const [imgError,     setImgError]     = useState(false);
    const [fullscreen,   setFullscreen]   = useState(false);

    // Build a set of "event frames" so we can badge them
    const eventFrameSet = new Set((throwingEvents || []).map(e => e.frame_idx));

    useEffect(() => {
        fetchFrameList(jobId)
            .then(d => { setFrames(d.frames || []); setLoading(false); })
            .catch(() => setLoading(false));
    }, [jobId]);

    const go = useCallback((dir) => {
        setImgError(false);
        setActiveIdx(i => (i + dir + frames.length) % frames.length);
    }, [frames.length]);

    // Keyboard navigation
    useEffect(() => {
        if (!fullscreen) return;
        const handler = (e) => {
            if (e.key === 'ArrowLeft')  go(-1);
            if (e.key === 'ArrowRight') go(1);
            if (e.key === 'Escape')     setFullscreen(false);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [fullscreen, go]);

    const currentFrame = frames[activeIdx];
    const isEventFrame = eventFrameSet.has(currentFrame);
    const timestampSec = fps && currentFrame != null ? (currentFrame / fps).toFixed(2) : null;

    if (loading) {
        return (
            <div className="bg-surface-container-lowest rounded-2xl p-10 flex items-center justify-center border border-outline-variant/5 shadow-sm">
                <div className="flex flex-col items-center gap-3 text-on-surface-variant">
                    <div className="w-8 h-8 border-2 border-primary rounded-full border-t-transparent animate-spin"></div>
                    <span className="text-sm font-bold">Loading annotated frames…</span>
                </div>
            </div>
        );
    }

    if (!frames.length) {
        return (
            <div className="bg-surface-container-lowest rounded-2xl p-10 flex items-center justify-center border border-outline-variant/5 shadow-sm text-on-surface-variant font-bold text-sm">
                <span className="material-symbols-outlined mr-2">image_not_supported</span>
                No annotated frames available for this session.
            </div>
        );
    }

    return (
        <>
            <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/5 overflow-hidden">
                {/* Header */}
                <div className="px-8 py-5 bg-surface-bright border-b border-surface-container flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">movie_filter</span>
                        <h3 className="text-base font-bold font-headline">Annotated Frame Gallery</h3>
                        <span className="ml-2 text-[10px] font-bold bg-primary-container/20 text-primary px-2 py-0.5 rounded-full">
                            {frames.length} frames
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs text-on-surface-variant font-mono">
                            Frame {activeIdx + 1} / {frames.length}
                        </span>
                        <button
                            onClick={() => setFullscreen(true)}
                            className="p-2 hover:bg-surface-container-high text-on-surface-variant hover:text-primary rounded-lg transition-colors"
                            title="Fullscreen"
                        >
                            <span className="material-symbols-outlined text-sm">fullscreen</span>
                        </button>
                    </div>
                </div>

                {/* Main Viewer */}
                <div className="relative bg-[#08100e] group" style={{ minHeight: 420 }}>
                    {imgError ? (
                        <div className="absolute inset-0 flex items-center justify-center text-outline-variant flex-col gap-2">
                            <span className="material-symbols-outlined text-4xl">broken_image</span>
                            <p className="text-sm">Frame could not be loaded</p>
                        </div>
                    ) : (
                        <img
                            key={currentFrame}
                            src={frameUrl(jobId, currentFrame)}
                            alt={`Annotated frame ${currentFrame}`}
                            onError={() => setImgError(true)}
                            className="w-full object-contain"
                            style={{ maxHeight: 520 }}
                        />
                    )}

                    {/* Event Badge */}
                    {isEventFrame && (
                        <div className="absolute top-4 left-4 flex items-center gap-2 bg-[#a83836]/90 backdrop-blur-sm text-white px-4 py-2 rounded-full text-xs font-bold shadow-lg animate-pulse">
                            <span className="material-symbols-outlined text-sm">warning</span>
                            LITTERING EVENT DETECTED
                        </div>
                    )}

                    {/* Timestamp badge */}
                    {timestampSec && (
                        <div className="absolute top-4 right-4 bg-black/60 backdrop-blur-sm text-white px-3 py-1.5 rounded-full text-xs font-mono font-bold">
                            ⏱ {timestampSec}s · Frame #{currentFrame}
                        </div>
                    )}

                    {/* Prev / Next arrows */}
                    <button
                        onClick={() => go(-1)}
                        className="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 hover:bg-black/80 backdrop-blur-sm text-white rounded-full flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-lg"
                    >
                        <span className="material-symbols-outlined">chevron_left</span>
                    </button>
                    <button
                        onClick={() => go(1)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-black/50 hover:bg-black/80 backdrop-blur-sm text-white rounded-full flex items-center justify-center transition-all opacity-0 group-hover:opacity-100 shadow-lg"
                    >
                        <span className="material-symbols-outlined">chevron_right</span>
                    </button>
                </div>

                {/* Thumbnail Strip */}
                <div className="p-4 bg-[#0d1a18] overflow-x-auto">
                    <div className="flex gap-2 min-w-max">
                        {frames.map((fi, ti) => {
                            const isEvent = eventFrameSet.has(fi);
                            const isActive = ti === activeIdx;
                            return (
                                <button
                                    key={fi}
                                    onClick={() => { setActiveIdx(ti); setImgError(false); }}
                                    className={`relative flex-shrink-0 rounded-lg overflow-hidden border-2 transition-all ${
                                        isActive
                                            ? 'border-primary scale-105 shadow-lg shadow-primary/30'
                                            : isEvent
                                            ? 'border-error/60 hover:border-error'
                                            : 'border-transparent hover:border-outline-variant/40'
                                    }`}
                                    style={{ width: 96, height: 54 }}
                                    title={`Frame ${fi}${isEvent ? ' ⚠ Event' : ''}`}
                                >
                                    <img
                                        src={frameUrl(jobId, fi)}
                                        alt=""
                                        loading="lazy"
                                        className="w-full h-full object-cover"
                                    />
                                    {isEvent && (
                                        <div className="absolute top-1 right-1 w-3 h-3 bg-error rounded-full shadow-sm"></div>
                                    )}
                                    {isActive && (
                                        <div className="absolute inset-0 bg-primary/10 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-white text-sm drop-shadow">play_circle</span>
                                        </div>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                    <p className="text-[10px] text-outline-variant mt-2 font-mono">
                        Scroll → to see all frames · <span className="text-error font-bold">Red dot</span> = littering event frame
                    </p>
                </div>
            </div>

            {/* Fullscreen Lightbox */}
            {fullscreen && (
                <div
                    className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center"
                    onClick={() => setFullscreen(false)}
                >
                    <div className="absolute top-4 right-4 flex items-center gap-3">
                        <span className="text-white/70 text-sm font-mono">Frame {activeIdx + 1} / {frames.length}</span>
                        <button
                            onClick={() => setFullscreen(false)}
                            className="w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center text-white transition-colors"
                        >
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    <img
                        key={`fs-${currentFrame}`}
                        src={frameUrl(jobId, currentFrame)}
                        alt={`Frame ${currentFrame}`}
                        className="max-w-[90vw] max-h-[85vh] object-contain rounded-xl shadow-2xl"
                        onClick={e => e.stopPropagation()}
                    />

                    {isEventFrame && (
                        <div className="absolute top-4 left-4 flex items-center gap-2 bg-[#a83836]/90 text-white px-4 py-2 rounded-full text-sm font-bold animate-pulse">
                            <span className="material-symbols-outlined text-sm">warning</span>
                            LITTERING EVENT DETECTED
                        </div>
                    )}

                    <div className="flex gap-4 mt-6" onClick={e => e.stopPropagation()}>
                        <button onClick={() => go(-1)} className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors flex items-center gap-2 font-bold text-sm">
                            <span className="material-symbols-outlined">chevron_left</span> Prev
                        </button>
                        <button onClick={() => go(1)} className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full transition-colors flex items-center gap-2 font-bold text-sm">
                            Next <span className="material-symbols-outlined">chevron_right</span>
                        </button>
                    </div>
                    <p className="text-white/40 text-xs mt-3">Use ← → arrow keys to navigate · ESC to close</p>
                </div>
            )}
        </>
    );
}


// ── Main AnalysisReport component ─────────────────────────────────────────────
export default function AnalysisReport({ data, jobId, onReset }) {
    if (!data) return null;

    const trackTimeline  = data.track_timeline  || [];
    const throwingEvents = data.throwing_events || [];
    const vlmDescs       = data.vlm_descriptions || [];
    const classCounts    = data.class_counts    || {};
    const totalFrames    = data.total_frames    ?? '—';
    const durationSec    = data.duration_sec    ?? 0;
    const fps            = data.fps             ?? null;
    const resolution     = (data.width && data.height) ? `${data.width}×${data.height}` : '—';
    const uniquePersons  = data.unique_persons  ?? 0;
    const uniqueTrash    = data.unique_trash    ?? 0;
    const totalEvents    = data.total_events    ?? 0;

    const mainSummary = vlmDescs.length > 0
        ? vlmDescs[0].description
        : 'No VLM semantic descriptions were generated for this session.';

    function downloadCsv(e) {
        e.preventDefault();
        const link = document.createElement('a');
        link.href = `/api/download/csv/${jobId}`;
        link.download = `trash_report_${jobId.substring(0, 8)}.csv`;
        link.target = '_self';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    return (
        <div className="p-10 flex gap-8 flex-grow overflow-hidden min-h-0">

            {/* Left sidebar */}
            <section className="w-72 flex flex-col space-y-4 flex-shrink-0">
                <div className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-outline-variant/5">
                    <h3 className="text-sm font-bold font-headline mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">video_library</span>
                        Active Session
                    </h3>
                    <div className="space-y-3">
                        <div className="p-3 bg-surface-container-low rounded-xl border-l-4 border-primary">
                            <p className="text-[10px] font-bold text-primary mb-1 uppercase tracking-widest">Currently Viewing</p>
                            <p className="text-sm font-semibold break-all font-mono">{jobId.substring(0, 16)}…</p>
                        </div>
                        <button
                            onClick={onReset}
                            className="w-full mt-2 p-3 bg-white hover:bg-surface-container-low rounded-xl border border-outline-variant/10 transition-colors text-sm font-bold text-on-surface-variant flex items-center justify-center gap-2"
                        >
                            <span className="material-symbols-outlined text-sm">home</span>
                            Return to Interface
                        </button>
                    </div>
                </div>

                <div className="bg-surface-container-lowest p-6 rounded-2xl shadow-sm border border-outline-variant/5 flex-1">
                    <h3 className="text-sm font-bold font-headline mb-4">Session Metadata</h3>
                    <div className="space-y-3">
                        {[
                            { label: 'Total Frames',   value: totalFrames },
                            { label: 'Duration',       value: `${durationSec.toFixed ? durationSec.toFixed(2) : durationSec}s` },
                            { label: 'Frame Rate',     value: `${fps || '—'} fps` },
                            { label: 'Resolution',     value: resolution },
                            { label: 'Unique Persons', value: uniquePersons },
                            { label: 'Unique Trash',   value: uniqueTrash },
                            { label: 'Events Flagged', value: totalEvents },
                        ].map(({ label, value }) => (
                            <div key={label} className="flex justify-between items-center border-b border-surface-container pb-2 last:border-0 last:pb-0">
                                <span className="text-xs text-on-surface-variant">{label}</span>
                                <span className="text-xs font-bold text-on-surface">{value}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Main scrollable content */}
            <section className="flex-1 overflow-y-auto pr-2 space-y-6 pb-8 min-h-0">

                {/* Report header */}
                <div className="flex justify-between items-end flex-wrap gap-4">
                    <div>
                        <span className="text-[10px] font-bold text-primary px-3 py-1 bg-primary-container/30 rounded-full uppercase tracking-widest">System Generated Report</span>
                        <h2 className="text-3xl font-extrabold font-headline mt-2 text-on-surface">Incident Semantic Analysis</h2>
                        <p className="text-on-surface-variant mt-1 text-sm">Ref: {jobId} · {data.generated_at || 'Just now'}</p>
                    </div>
                    <button
                        onClick={downloadCsv}
                        className="flex items-center px-6 py-2.5 rounded-xl primary-gradient text-white text-sm font-semibold shadow-lg hover:scale-105 transition-transform"
                    >
                        <span className="material-symbols-outlined mr-2">file_download</span>
                        Export CSV
                    </button>
                </div>

                {/* Stat chips */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {[
                        { label: 'Persons Detected', value: uniquePersons, icon: 'person',     color: 'text-primary' },
                        { label: 'Trash Items',       value: uniqueTrash,   icon: 'delete',     color: 'text-error' },
                        { label: 'Throwing Events',   value: totalEvents,   icon: 'warning',    color: 'text-tertiary' },
                        { label: 'VLM Descriptions',  value: vlmDescs.length,icon: 'visibility',color: 'text-secondary' },
                        {
                            label: 'CLIP Verified',
                            value: throwingEvents.filter(e => e.clip_is_littering).length,
                            icon: 'verified',
                            color: throwingEvents.some(e => e.clip_is_littering) ? 'text-error' : 'text-green-400',
                        },
                    ].map(({ label, value, icon, color }) => (
                        <div key={label} className="bg-surface-container-lowest p-5 rounded-2xl shadow-sm border border-outline-variant/5 flex flex-col gap-2">
                            <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                            <p className="text-2xl font-black font-headline text-on-surface">{value}</p>
                            <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{label}</p>
                        </div>
                    ))}
                </div>

                {/* ─── FRAME GALLERY ─── */}
                <FrameGallery jobId={jobId} throwingEvents={throwingEvents} fps={fps} />

                {/* VLM Semantic Summary */}
                <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-outline-variant/5 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-40 h-40 primary-gradient opacity-5 rounded-bl-[100px]"></div>
                    <h3 className="text-base font-bold font-headline mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">summarize</span>
                        Semantic Scene Summary
                        <span className="ml-auto text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                            CLIP + {vlmDescs[0]?.description?.startsWith('[CLIP') ? 'CLIP fallback' : 'Gemini'}
                        </span>
                    </h3>
                    <p className="text-sm text-on-surface-variant leading-relaxed bg-surface-container/40 p-4 rounded-xl font-mono">
                        {mainSummary}
                    </p>
                    {vlmDescs.length > 1 && (
                        <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
                            {vlmDescs.slice(1).map((vd, i) => {
                                // Find nearest throwing event with CLIP data
                                const nearEvt = throwingEvents.find(
                                    e => e.clip_label && Math.abs(e.timestamp - vd.timestamp) < 3
                                );
                                return (
                                    <div key={i} className="flex flex-col gap-2 p-3 bg-surface-container-low rounded-xl">
                                        <div className="flex gap-3 items-start">
                                            <span className="text-[10px] font-bold text-primary bg-primary-container/20 px-2 py-1 rounded-md shrink-0">
                                                {vd.time_formatted || `${vd.timestamp?.toFixed(1)}s`}
                                            </span>
                                            <p className="text-xs text-on-surface-variant font-mono leading-snug">{vd.description}</p>
                                        </div>
                                        {nearEvt && (
                                            <CLIPVerification
                                                clipLabel={nearEvt.clip_label}
                                                clipConfidence={nearEvt.clip_confidence}
                                                clipIsLittering={nearEvt.clip_is_littering}
                                                clipAllScores={nearEvt.clip_all_scores}
                                            />
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Class Breakdown */}
                {Object.keys(classCounts).length > 0 && (
                    <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-outline-variant/5">
                        <h3 className="text-base font-bold font-headline mb-6 flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary">bar_chart</span>
                            Detection Class Breakdown
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                            {Object.entries(classCounts).map(([cls, count]) => (
                                <div key={cls} className="bg-surface-container-low px-5 py-4 rounded-xl flex flex-col gap-1">
                                    <p className="text-[10px] text-on-surface-variant font-bold uppercase tracking-widest truncate">{cls}</p>
                                    <p className="text-3xl font-headline font-black text-primary">{count}</p>
                                    <p className="text-[10px] text-on-surface-variant">detections</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Throwing Events */}
                {throwingEvents.length > 0 && (
                    <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/5 overflow-hidden">
                        <div className="px-8 py-5 bg-error-container/10 border-b border-surface-container flex items-center gap-2">
                            <span className="material-symbols-outlined text-error">warning</span>
                            <h3 className="text-base font-bold font-headline text-error">
                                Littering / Throwing Events ({throwingEvents.length})
                            </h3>
                            {throwingEvents.some(e => e.clip_is_littering) && (
                                <span className="ml-auto text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-full">
                                    {throwingEvents.filter(e => e.clip_is_littering).length} CLIP-confirmed
                                </span>
                            )}
                        </div>
                        <div className="divide-y divide-surface-container">
                            {throwingEvents.map((evt, i) => (
                                <div key={i} className="px-8 py-5 flex flex-col gap-3 hover:bg-surface-container-low transition-colors">
                                    <div className="flex items-start gap-5">
                                        <span className="bg-error-container/20 text-error text-xs font-bold px-2 py-1 rounded-md shrink-0">#{i + 1}</span>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-on-surface">{evt.description}</p>
                                            <p className="text-xs text-on-surface-variant mt-1 font-mono">
                                                {evt.time_formatted || `${evt.timestamp?.toFixed(2)}s`} · Frame {evt.frame_idx}
                                            </p>
                                        </div>
                                        {/* Compact CLIP badge */}
                                        {evt.clip_label && (
                                            <CLIPVerification
                                                clipLabel={evt.clip_label}
                                                clipConfidence={evt.clip_confidence}
                                                clipIsLittering={evt.clip_is_littering}
                                                clipAllScores={evt.clip_all_scores}
                                                compact={true}
                                            />
                                        )}
                                    </div>
                                    {/* Full CLIP breakdown – show when littering confirmed or high confidence */}
                                    {evt.clip_label && Object.keys(evt.clip_all_scores || {}).length > 0 && (
                                        <div className="ml-10">
                                            <CLIPVerification
                                                clipLabel={evt.clip_label}
                                                clipConfidence={evt.clip_confidence}
                                                clipIsLittering={evt.clip_is_littering}
                                                clipAllScores={evt.clip_all_scores}
                                                compact={false}
                                            />
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Track Timeline Table */}
                {trackTimeline.length > 0 && (
                    <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-outline-variant/5 overflow-hidden">
                        <div className="px-8 py-5 bg-surface-bright border-b border-surface-container flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary">analytics</span>
                            <h3 className="text-base font-bold font-headline">Tracked Objects Registry</h3>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="bg-surface-container-low/50">
                                        {['Track ID', 'Class', 'Model', 'First Seen', 'Last Seen', 'Detections'].map(h => (
                                            <th key={h} className="px-6 py-3 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-surface-container">
                                    {trackTimeline.map((track, i) => (
                                        <tr key={i} className="hover:bg-surface-container-low/50 transition-colors">
                                            <td className="px-6 py-4 font-mono text-sm font-semibold">#{track.track_id}</td>
                                            <td className="px-6 py-4">
                                                <span className="bg-surface-container-high text-on-surface px-2 py-1 rounded-md text-xs font-bold uppercase">{track.class_name}</span>
                                            </td>
                                            <td className="px-6 py-4 text-xs text-on-surface-variant">{track.source_model}</td>
                                            <td className="px-6 py-4 text-xs font-mono text-on-surface-variant">{track.first_seen_fmt || `${track.first_seen?.toFixed(2)}s`}</td>
                                            <td className="px-6 py-4 text-xs font-mono text-on-surface-variant">{track.last_seen_fmt  || `${track.last_seen?.toFixed(2)}s`}</td>
                                            <td className="px-6 py-4 text-sm font-bold text-primary">{track.detections}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

            </section>
        </div>
    );
}
