import React from "react";
import styles from "./CLIPVerification.module.css";

/**
 * CLIPVerification — shows CLIP zero-shot classification results
 * for a single throwing event.
 *
 * Props:
 *   clipLabel      {string}  — winning label text
 *   clipConfidence {number}  — confidence [0,1]
 *   clipIsLittering {bool}   — did CLIP confirm littering?
 *   clipAllScores  {object}  — { label: prob } for all labels
 *   compact        {bool}    — show only badge (no bars)
 */
const CLIPVerification = ({
  clipLabel = "",
  clipConfidence = 0,
  clipIsLittering = false,
  clipAllScores = {},
  compact = false,
}) => {
  const hasScores = Object.keys(clipAllScores).length > 0;
  const confPct = Math.round(clipConfidence * 100);

  if (!clipLabel) {
    return (
      <div className={styles.noData}>
        <span className={styles.noDataIcon}>◎</span>
        CLIP — not yet analysed
      </div>
    );
  }

  const verdict = clipIsLittering ? "confirmed" : "unlikely";
  const verdictClass = clipIsLittering ? styles.confirmed : styles.unlikely;

  if (compact) {
    return (
      <div className={`${styles.badge} ${verdictClass}`}>
        <span className={styles.badgeIcon}>{clipIsLittering ? "⚠" : "✓"}</span>
        <span className={styles.badgeText}>
          CLIP: {confPct}%&nbsp;{clipIsLittering ? "Littering" : "Safe"}
        </span>
      </div>
    );
  }

  // Sort scores descending
  const sorted = Object.entries(clipAllScores).sort(([, a], [, b]) => b - a);
  const maxProb = sorted.length > 0 ? sorted[0][1] : 1;

  return (
    <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.modelTag}>CLIP</span>
          <span className={styles.modelSub}>zero-shot</span>
        </div>
        <div className={`${styles.verdict} ${verdictClass}`}>
          {clipIsLittering ? "⚠ Littering Confirmed" : "✓ No Littering"}
        </div>
      </div>

      {/* Top label */}
      <div className={styles.topLabel}>
        <span className={styles.topLabelText} title={clipLabel}>
          "{clipLabel}"
        </span>
        <span className={styles.topConf}>{confPct}%</span>
      </div>

      {/* Confidence bars */}
      {hasScores && (
        <div className={styles.bars}>
          {sorted.map(([label, prob]) => {
            const pct = Math.round(prob * 100);
            const widthPct = Math.round((prob / maxProb) * 100);
            const isLitterLabel =
              label.includes("throwing") || label.includes("dropping");
            const isTop = label === clipLabel;
            return (
              <div key={label} className={styles.barRow}>
                <div
                  className={`${styles.barLabel} ${isTop ? styles.barLabelTop : ""}`}
                  title={label}
                >
                  {label}
                </div>
                <div className={styles.barTrack}>
                  <div
                    className={`${styles.barFill} ${
                      isLitterLabel ? styles.barDanger : styles.barSafe
                    } ${isTop ? styles.barTop : ""}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
                <div className={styles.barPct}>{pct}%</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default CLIPVerification;
