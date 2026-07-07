import { useEffect, useRef } from 'react';

export const useIdleLogout = (onIdle) => {
  const timeoutRef = useRef(null);

  const timeoutSeconds = parseInt(import.meta.env.VITE_KIOSK_IDLE_LOGOUT_SECONDS || '30', 10);

  useEffect(() => {
    const handleIdle = () => {
      if (onIdle) onIdle();
    };

    const resetTimer = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(handleIdle, timeoutSeconds * 1000);
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
  }, [onIdle, timeoutSeconds]);
};