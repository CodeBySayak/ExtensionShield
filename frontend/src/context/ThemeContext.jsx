import React, { createContext, useContext, useState, useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

// Routes that should always use dark mode (except homepage)
const FORCE_DARK_ROUTES = ["/settings", "/reports"];

export const ThemeProvider = ({ children }) => {
  const location = useLocation();
  const [theme, setTheme] = useState(() => {
    // Check localStorage first, then system preference, then default to dark
    const stored = localStorage.getItem("theme");
    if (stored) {
      return stored;
    }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  });

  // Determine effective theme based on route
  const effectiveTheme = useMemo(() => {
    // Force dark mode on specific routes (but not homepage)
    if (location.pathname !== "/" && FORCE_DARK_ROUTES.some(route => location.pathname.startsWith(route))) {
      return "dark";
    }
    return theme;
  }, [theme, location.pathname]);

  useEffect(() => {
    // Apply effective theme to document
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(effectiveTheme);
    
    // Update CSS variables based on effective theme
    if (effectiveTheme === "light") {
      document.documentElement.style.backgroundColor = "#ffffff";
      document.body.style.backgroundColor = "#ffffff";
    } else {
      document.documentElement.style.backgroundColor = "#0d1424";
      document.body.style.backgroundColor = "#0d1424";
    }
    
    // Save actual theme (not effective theme) to localStorage
    if (effectiveTheme === theme) {
      localStorage.setItem("theme", theme);
    }
  }, [effectiveTheme, theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <ThemeContext.Provider value={{ theme: effectiveTheme, toggleTheme, setTheme, actualTheme: theme }}>
      {children}
    </ThemeContext.Provider>
  );
};

