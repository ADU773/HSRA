import React from "react";
import styles from "./VlmDescriptions.module.css";
import CLIPVerification from "./CLIPVerification";

/**
 * VlmDescriptions — renders VLM scene description text AND CLIP scores
 * for a list of vlm_descriptions from the analysis report.
 *
 * Props:
 *   descriptions  {Array} — vlm_descriptions array from report JSON
 *   throwingEvents {Array} — throwing_events array (for CLIP scores per timestamp)
 */
const VlmDescriptions = ({ descriptions = [], throwingEvents = [] }) => {
  if (!descriptions.length) {
    return (
      <div className={styles.empty}>No VLM scene descriptions available.</div>
    );
  }

  // Build a quick map: timestamp→nearest event with CLIP data
  const eventsByTimestamp = {};
  throwingEvents.forEach((evt) => {
    if (evt.clip_label) {
      const key = Math.round(evt.timestamp);
      if (!eventsByTimestamp[key]) eventsByTimestamp[key] = evt;
    }
  });

  return (
    <div className={styles.list}>
      {descriptions.map((d, i) => {
        const nearKey = Math.round(d.timestamp);
        const nearEvent = eventsByTimestamp[nearKey];

        return (
          <div key={i} className={styles.item}>
            {/* Timestamp badge */}
            <div className={styles.timeBadge}>
              {formatTime(d.timestamp)}
            </div>

            {/* Scene description text */}
            <p className={styles.text}>{d.description}</p>

            {/* CLIP result if a nearby event exists */}
            {nearEvent && (
              <div className={styles.clipWrap}>
                <CLIPVerification
                  clipLabel={nearEvent.clip_label}
                  clipConfidence={nearEvent.clip_confidence}
                  clipIsLittering={nearEvent.clip_is_littering}
                  clipAllScores={nearEvent.clip_all_scores}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

function formatTime(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default VlmDescriptions;
