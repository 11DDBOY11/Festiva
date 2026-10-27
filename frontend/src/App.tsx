import React, { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { AuthPage } from "./pages/AuthPage";
import { EventsPage } from "./pages/EventsPage";
import { User, getCurrentUser } from "./lib/api";

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-400 font-medium">Loading Festiva AI...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Navbar user={currentUser} />
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
