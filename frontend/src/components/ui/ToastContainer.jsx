import { useEffect } from "react";

export default function ToastContainer({ toast, clearToast }) {
  useEffect(() => {
    if (!toast) return;

    const timer = setTimeout(() => {
      clearToast();
    }, 3000);

    return () => clearTimeout(timer);
  }, [toast, clearToast]);

  if (!toast) return null;

  return <div className="fixed bottom-8 right-8 z-[9999]">{toast}</div>;
}
