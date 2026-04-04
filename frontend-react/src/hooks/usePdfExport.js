/**
 * usePdfExport.js
 *
 * Two export strategies:
 *   1. downloadServerPdf(jobId)  — fetches /api/download/pdf/<jobId>
 *      → structured ReportLab PDF, always complete & paginated
 *
 *   2. downloadClientPdf(ref, jobId) — html2canvas + jsPDF screenshot
 *      → visual clone of the report page
 */
import { useState } from "react";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

export function usePdfExport() {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  /** Download structured PDF from backend */
  async function downloadServerPdf(jobId) {
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetch(`/api/download/pdf/${jobId}`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
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

  /** Capture visible report DOM as a visual PDF (client-side) */
  async function downloadClientPdf(reportRef, jobId) {
    if (!reportRef?.current) return;
    setExporting(true);
    setExportError(null);
    try {
      const element = reportRef.current;
      const canvas = await html2canvas(element, {
        scale: 1.5,
        useCORS: true,
        backgroundColor: "#0f172a",
        logging: false,
        allowTaint: true,
      });

      const imgData = canvas.toDataURL("image/jpeg", 0.92);
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const imgW = pageW;
      const imgH = (canvas.height * imgW) / canvas.width;

      let yPos = 0;
      let remainingH = imgH;

      while (remainingH > 0) {
        pdf.addImage(imgData, "JPEG", 0, -yPos, imgW, imgH);
        remainingH -= pageH;
        yPos += pageH;
        if (remainingH > 0) pdf.addPage();
      }

      pdf.save(`trashguard_visual_${jobId.substring(0, 8)}.pdf`);
    } catch (err) {
      setExportError(err.message);
    } finally {
      setExporting(false);
    }
  }

  return { exporting, exportError, downloadServerPdf, downloadClientPdf };
}
