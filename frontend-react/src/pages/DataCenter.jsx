import React, { useState, useEffect } from 'react';

export default function DataCenter() {
    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/jobs')
            .then(res => res.json())
            .then(data => {
                // Ensure data is sorted by latest (assuming the backend API returns them in whatever order)
                // We'll reverse them to roughly put newest first if ordered by time insertion
                setJobs(data.reverse()); 
                setLoading(false);
            })
            .catch(() => {
                setLoading(false);
            });
    }, []);

    return (
        <section className="p-10 flex-1 flex flex-col h-full overflow-hidden">
            <div className="mb-8 flex-shrink-0">
                <h2 className="text-3xl font-extrabold text-on-surface font-headline tracking-tight">Data & Logs Center</h2>
                <p className="text-on-surface-variant mt-1">Audit historical inference results and export detection metadata.</p>
            </div>

            {/* Bento Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 flex-shrink-0">
                <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm flex justify-between items-center border border-outline-variant/10">
                    <div>
                        <p className="text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">Total Active Jobs</p>
                        <p className="text-2xl font-black text-on-surface mt-1">{jobs.length}</p>
                    </div>
                    <div className="w-12 h-12 bg-secondary-container/30 rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-secondary">monitoring</span>
                    </div>
                </div>
                <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm flex justify-between items-center border border-outline-variant/10">
                    <div>
                        <p className="text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">Completed Jobs</p>
                        <p className="text-2xl font-black text-on-surface mt-1">{jobs.filter(j => j.status === 'done').length}</p>
                    </div>
                    <div className="w-12 h-12 bg-primary-container/30 rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-primary">verified</span>
                    </div>
                </div>
                <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm flex justify-between items-center border border-outline-variant/10">
                    <div>
                        <p className="text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">Avg Latency</p>
                        <p className="text-2xl font-black text-on-surface mt-1">11.4ms</p>
                    </div>
                    <div className="w-12 h-12 bg-tertiary-container/30 rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-tertiary">speed</span>
                    </div>
                </div>
            </div>

            {/* Table Section */}
            <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/10 flex-1 flex flex-col min-h-0">
                <div className="px-8 py-6 border-b border-surface-container flex justify-between items-center bg-surface-bright flex-shrink-0">
                    <h3 className="font-headline font-bold text-on-surface">Historical Inference Reports</h3>
                    <div className="flex space-x-3">
                        <button className="p-2 bg-surface-container-low text-on-surface-variant rounded-lg hover:bg-surface-container-high transition-colors">
                            <span className="material-symbols-outlined text-sm">filter_list</span>
                        </button>
                    </div>
                </div>

                <div className="overflow-y-auto flex-1">
                    {loading ? (
                        <div className="flex items-center justify-center h-48">
                            <span className="text-outline-variant font-bold text-sm">Loading Historical Logs...</span>
                        </div>
                    ) : (
                        <table className="w-full text-left border-collapse">
                            <thead className="sticky top-0 bg-surface-container-lowest z-10 shadow-sm border-b border-surface-container-high">
                                <tr className="bg-surface-container-low/50">
                                    <th className="px-8 py-4 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">Job ID</th>
                                    <th className="px-8 py-4 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">Status</th>
                                    <th className="px-8 py-4 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest flex-1">Last Message</th>
                                    <th className="px-8 py-4 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest text-right">Reports</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-surface-container">
                                {jobs.length === 0 ? (
                                    <tr><td colSpan="4" className="px-8 py-8 text-center text-outline-variant font-bold">No jobs run yet.</td></tr>
                                ) : jobs.map(job => (
                                    <tr key={job.id} className="hover:bg-surface-container-low/50 transition-colors group">
                                        <td className="px-8 py-4">
                                            <div className="text-sm font-semibold font-mono truncate max-w-[150px]">{job.id}</div>
                                        </td>
                                        <td className="px-8 py-4">
                                            <span className={`px-3 py-1 text-[10px] font-bold rounded-full uppercase tracking-widest ${
                                                job.status === 'done' ? 'bg-primary-container/20 text-on-primary-container' :
                                                job.status === 'running' ? 'bg-secondary-container/40 text-on-secondary-container animate-pulse' :
                                                job.status === 'error' ? 'bg-error-container/20 text-error' :
                                                'bg-surface-container text-on-surface-variant'
                                            }`}>
                                                {job.status}
                                            </span>
                                        </td>
                                        <td className="px-8 py-4 font-mono text-xs text-on-surface-variant truncate max-w-[300px]" title={job.message}>
                                            {job.message || '-'}
                                        </td>
                                        <td className="px-8 py-4 text-right">
                                            <div className="flex justify-end space-x-2">
                                                {job.status === 'done' ? (
                                                    <a href={`/api/download/csv/${job.id}`} download className="p-2 hover:bg-primary-container/20 text-primary rounded-lg transition-colors bg-surface-container" title="Download CSV">
                                                        <span className="material-symbols-outlined text-sm">file_download</span>
                                                    </a>
                                                ) : (
                                                    <button className="p-2 text-outline-variant rounded-lg cursor-not-allowed">
                                                        <span className="material-symbols-outlined text-sm">file_download_off</span>
                                                    </button>
                                                )}
                                                <button className="p-2 hover:bg-surface-container-high text-on-surface-variant rounded-lg transition-colors">
                                                    <span className="material-symbols-outlined text-sm">more_vert</span>
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </section>
    );
}
