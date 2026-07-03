import { useEffect, useRef } from "react";

import { PARTICIPANT_DECLARATIONS } from "../content/participantDeclarations.js";

function isScrolledToBottom(element) {
  return element.scrollTop + element.clientHeight >= element.scrollHeight - 12;
}

export default function DeclarationsPanel({ reviewed, onReviewed }) {
  const panelRef = useRef(null);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel || reviewed) {
      return;
    }

    if (panel.scrollHeight <= panel.clientHeight + 1) {
      onReviewed();
    }
  }, [onReviewed, reviewed]);

  function handleScroll(event) {
    if (!reviewed && isScrolledToBottom(event.currentTarget)) {
      onReviewed();
    }
  }

  return (
    <div className="declarations-panel" onScroll={handleScroll} ref={panelRef}>
      <ol className="declarations-list">
        {PARTICIPANT_DECLARATIONS.map((item, index) => (
          <li key={item.title}>
            <strong>
              {index + 1}. {item.title}
            </strong>
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
    </div>
  );
}
