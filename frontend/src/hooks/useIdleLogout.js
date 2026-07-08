import { useEffect, useRef } from 'react';

export const useIdleLogout = ({ enabled, onIdle, timeoutSeconds }) => {
  const timeoutRef = useRef(null);

  const envTimeoutSeconds = parseInt(import.meta.env.VITE_KIOSK_IDLE_LOGOUT_SECONDS || '30', 10);
  const defaultTimeoutSeconds =
    Number.isFinite(envTimeoutSeconds) && envTimeoutSeconds > 0 ? envTimeoutSeconds : 30;
  const effectiveTimeoutSeconds =
    Number.isFinite(timeoutSeconds) && timeoutSeconds > 0
      ? timeoutSeconds
      : defaultTimeoutSeconds;

  useEffect(() => {
    if (!enabled) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      return undefined;
    }

    const handleIdle = () => {
      if (onIdle) onIdle();
    };

    const resetTimer = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(handleIdle, effectiveTimeoutSeconds * 1000);
    };

    const events = [
      'mousemove', 'keydown', 'wheel', 'mousedown', 'touchstart', 'touchmove'
    ];

    events.forEach(event =>
      document.addEventListener(event, resetTimer, { passive: true })
    );

    resetTimer();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      events.forEach(event =>
        document.removeEventListener(event, resetTimer)
      );
    };
  }, [enabled, onIdle, effectiveTimeoutSeconds]);
};
