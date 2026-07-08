import { useEffect, useRef } from "react";

import { PARTICIPANT_DECLARATIONS } from "../content/participantDeclarations.js";

export default function DeclarationsPanel({ reviewed, onReviewed }) {
  const panelRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    const panel = panelRef.current;
    const bottom = bottomRef.current;
    if (!panel || !bottom || reviewed) {
      return undefined;
    }

    if (panel.scrollHeight <= panel.clientHeight + 1) {
      onReviewed();
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onReviewed();
        }
      },
      {
        root: panel,
        threshold: 0,
      },
    );

    observer.observe(bottom);

    return () => observer.disconnect();
  }, [onReviewed, reviewed]);

  return (
    <div className="declarations-panel" ref={panelRef}>
      <ol className="declarations-list">
        {PARTICIPANT_DECLARATIONS.map((item) => (
          <li key={item.title}>
            <strong>{item.title}</strong>
            {item.body && <p>{item.body}</p>}
            {item.bullets && (
              <ul>
                {item.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
      <div ref={bottomRef} className="declarations-panel-sentinel" aria-hidden="true" />
    </div>
  );
}
