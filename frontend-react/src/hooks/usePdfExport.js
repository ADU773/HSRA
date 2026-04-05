/**
 * usePdfExport.js
 *
 * Downloads the server-generated text-based PDF report.
 * The PDF is built by ReportLab on the backend (pdf_report.py)
 * and contains proper text, headings, tables — not screenshots.
 */
import { useState } from "react";

export function usePdfExport() {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  /** Download the structured text PDF from the backend */
  async function downloadPdf(jobId) {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(`/api/download/pdf/${jobId}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Server returned ${res.status}`);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `trashguard_report_${jobId.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err.message);
    } finally {
      setExporting(false);
    }
  }

  return { exporting, exportError, downloadPdf };
}
