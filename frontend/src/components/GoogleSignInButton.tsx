import React, { useEffect, useRef, useState } from "react";

/**
 * Renders the official Google Identity Services sign-in button and hands the
 * resulting ID-token credential to the caller for server-side verification.
 */

declare global {
  interface Window {
    google?: any;
  }
}

const GSI_SRC = "https://accounts.google.com/gsi/client";

let gsiLoader: Promise<void> | null = null;

function loadGsi(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!gsiLoader) {
    gsiLoader = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = GSI_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        gsiLoader = null;
        reject(new Error("Could not load Google Sign-In"));
      };
      document.head.appendChild(script);
    });
  }
  return gsiLoader;
}

interface Props {
  clientId: string;
  onCredential: (credential: string) => void;
  onError?: (message: string) => void;
  text?: "signin_with" | "continue_with" | "signup_with";
}

export default function GoogleSignInButton({ clientId, onCredential, onError, text = "continue_with" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGsi()
      .then(() => {
        if (cancelled || !ref.current || !window.google?.accounts?.id) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (resp: { credential?: string }) => {
            if (resp?.credential) onCredential(resp.credential);
            else onError?.("Google sign-in was cancelled.");
          },
        });
        window.google.accounts.id.renderButton(ref.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text,
          shape: "pill",
        });
      })
      .catch((e) => {
        if (!cancelled) {
          setFailed(true);
          onError?.(e?.message || "Could not load Google Sign-In");
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  if (failed) {
    return (
      <p className="text-sm text-red-300 text-center">
        Google Sign-In could not be loaded. Check your connection and retry.
      </p>
    );
  }
  return <div ref={ref} className="flex justify-center" />;
}
