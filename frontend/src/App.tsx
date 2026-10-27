import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { AuthPage } from "./pages/AuthPage";
import { EventsPage } from "./pages/EventsPage";
import { User, getCurrentUser } from "./lib/api";

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Default theme is LIGHT as requested
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("festiva_theme");
    return saved === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("festiva_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const checkUser = async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch {
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkUser();

    // Listen to token changes across tabs or silent refreshes
    const handleAuthChange = () => {
      checkUser();
    };

    window.addEventListener("festiva_auth_change", handleAuthChange);
    return () => {
      window.removeEventListener("festiva_auth_change", handleAuthChange);
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
            Loading Festiva AI...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-stone-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      <Navbar user={currentUser} theme={theme} onToggleTheme={toggleTheme} />
      <main className="flex-1">
        {currentUser ? (
          <EventsPage />
        ) : (
          <AuthPage onAuthSuccess={checkUser} />
        )}
      </main>
    </div>
  );
};

export default App;
