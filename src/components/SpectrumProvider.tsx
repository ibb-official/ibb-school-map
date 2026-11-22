"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Provider } from "@react-spectrum/s2/Provider";
import { ColorSchemePref } from "@/data/types";
import { loadUserPrefs, saveUserPrefs } from "@/scene/prefs";

interface ThemeContextValue {
  colorScheme: ColorSchemePref;
  setColorScheme: (next: ColorSchemePref) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  colorScheme: "light",
  setColorScheme: () => {},
});

export function useSpectrumTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

function applyRootColorSchemeAttr(pref: ColorSchemePref): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (pref === "system") {
    root.removeAttribute("data-color-scheme");
  } else {
    root.setAttribute("data-color-scheme", pref);
  }
}

export function SpectrumProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [colorScheme, setColorSchemeState] = useState<ColorSchemePref>("light");

  useEffect(() => {
    const prefs = loadUserPrefs();
    setColorSchemeState(prefs.colorScheme);
    applyRootColorSchemeAttr(prefs.colorScheme);
  }, []);

  const setColorScheme = useCallback((next: ColorSchemePref) => {
    setColorSchemeState(next);
    applyRootColorSchemeAttr(next);
    const current = loadUserPrefs();
    saveUserPrefs({ ...current, colorScheme: next });
  }, []);

  return (
    <ThemeContext.Provider value={{ colorScheme, setColorScheme }}>
      <Provider
        locale="zh-CN"
        colorScheme={colorScheme === "system" ? undefined : colorScheme}
        background="base"
        router={{
          navigate: (href) => {
            if (/^https?:\/\//.test(href)) {
              window.open(href, "_blank", "noopener,noreferrer");
            } else {
              router.push(href);
            }
          },
          useHref: (href) => href,
        }}
        UNSAFE_className="spectrum-app-root"
      >
        {children}
      </Provider>
    </ThemeContext.Provider>
  );
}
