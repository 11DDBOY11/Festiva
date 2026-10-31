import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { AuthPage } from "./pages/AuthPage";
import { EventsPage } from "./pages/EventsPage";
import { LandingPage } from "./pages/LandingPage";
import { User, getCurrentUser, ServerStatusDetail } from "./lib/api";

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [serverStatus, setServerStatus] = useState<ServerStatusDetail | null>(null);

  // Navigation state for logged-out visitors
  const [loggedOutView, setLoggedOutView] = useState<"landing" | "login" | "register">(() => {
    const hash = window.location.hash.toLowerCase();
    if (hash === "#login") return "login";
    if (hash === "#register") return "register";
    return "landing";
  });

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

    const handleHashChange = () => {
      const hash = window.location.hash.toLowerCase();
      if (hash === "#login") setLoggedOutView("login");
      else if (hash === "#register") setLoggedOutView("register");
      else if (hash === "" || hash === "#") setLoggedOutView("landing");
    };

    const handleServerStatus = (e: Event) => {
      const detail = (e as CustomEvent<ServerStatusDetail>).detail;
      if (detail && detail.waking) {
        setServerStatus(detail);
      } else {
        setServerStatus(null);
      }
    };

    window.addEventListener("festiva_auth_change", handleAuthChange);
    window.addEventListener("hashchange", handleHashChange);
    window.addEventListener("festiva_server_status", handleServerStatus);
    return () => {
      window.removeEventListener("festiva_auth_change", handleAuthChange);
      window.removeEventListener("hashchange", handleHashChange);
      window.removeEventListener("festiva_server_status", handleServerStatus);
    };
  }, []);

  const navigateToLogin = () => {
    setLoggedOutView("login");
    window.location.hash = "#login";
  };

  const navigateToRegister = () => {
    setLoggedOutView("register");
    window.location.hash = "#register";
  };

  const navigateToLanding = () => {
    setLoggedOutView("landing");
    window.location.hash = "";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
            Loading Festiva...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-stone-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {serverStatus?.waking && (
        <aside
          role="status"
          aria-live="polite"
          className="bg-amber-500 text-stone-950 px-4 py-2 text-xs font-semibold flex items-center justify-center gap-2 sticky top-0 z-50 shadow-md"
        >
          <div className="w-2 h-2 rounded-full bg-stone-950 animate-ping" />
          <span>
            Waking up the server... Render free tier spins down after inactivity (attempt {serverStatus.attempt || 1}/{serverStatus.maxAttempts || 12}, ~60s). Please hold on...
          </span>
        </aside>
      )}
      <Navbar
        user={currentUser}
        theme={theme}
        onToggleTheme={toggleTheme}
        onLogoClick={currentUser ? undefined : navigateToLanding}
        onSignInClick={currentUser ? undefined : navigateToLogin}
      />
      <main className="flex-1 flex flex-col">
        {currentUser ? (
          <EventsPage />
        ) : loggedOutView === "landing" ? (
          <LandingPage
            onNavigateLogin={navigateToLogin}
            onNavigateRegister={navigateToRegister}
            onDemoSuccess={checkUser}
          />
        ) : (
          <AuthPage
            initialMode={loggedOutView}
            onAuthSuccess={checkUser}
            onBackToLanding={navigateToLanding}
          />
        )}
      </main>
    </div>
  );
};

export default App;
