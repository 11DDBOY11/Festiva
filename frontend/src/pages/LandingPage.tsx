import React, { useState } from "react";
import {
  Sparkles,
  ArrowRight,
  Calendar,
  CheckCircle2,
  FileText,
  SlidersHorizontal,
  Clock,
  CheckSquare,
  GitCompare,
  Mail,
  Download,
  ShieldCheck,
  PlayCircle,
} from "lucide-react";
import { login, register } from "../lib/api";

interface LandingPageProps {
  onNavigateLogin: () => void;
  onNavigateRegister: () => void;
  onDemoSuccess: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onNavigateLogin,
  onNavigateRegister,
  onDemoSuccess,
}) => {
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  const handleTryDemo = async () => {
    setDemoLoading(true);
    setDemoError(null);
    try {
      // Set flag to auto-open the birthday demo event once authenticated
      sessionStorage.setItem("festiva_auto_open_demo", "true");

      const demoEmail = "demo@festiva.ai";
      const demoPass = "DemoFestiva2026!";

      try {
        await login(demoEmail, demoPass);
      } catch {
        // Fallback: register if account doesn't exist on this database yet
        try {
          await register("Festiva Demo", demoEmail, demoPass);
        } catch {
          // Ignore registration error if user was already present
        }
        await login(demoEmail, demoPass);
      }

      onDemoSuccess();
    } catch (err: any) {
      sessionStorage.removeItem("festiva_auto_open_demo");
      setDemoError(err.message || "Failed to load demo. Please try logging in manually.");
      setDemoLoading(false);
    }
  };

  const handleCreateEvent = () => {
    sessionStorage.setItem("festiva_auto_open_create", "true");
    onNavigateRegister();
  };

  return (
    <div className="w-full flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-28 border-b border-slate-200 dark:border-slate-800 bg-gradient-to-b from-amber-500/5 via-transparent to-transparent">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs sm:text-sm font-semibold mb-6 shadow-sm">
            <Sparkles className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span>Intelligent Celebration & Event Planning Copilot</span>
            <span className="hidden sm:inline-block text-amber-600/60 dark:text-amber-400/60">•</span>
            <span className="hidden sm:inline-block">Mangaluru, Karnataka</span>
          </div>

          {/* Product Headline & Pitch */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 dark:text-white font-display max-w-4xl mx-auto leading-tight sm:leading-tight">
            Plan celebrations with complete{" "}
            <span className="bg-gradient-to-r from-amber-600 via-orange-600 to-amber-700 dark:from-amber-300 dark:via-orange-300 dark:to-amber-400 bg-clip-text text-transparent">
              clarity & confidence
            </span>
          </h1>

          <p className="mt-5 text-lg sm:text-xl text-slate-700 dark:text-slate-300 max-w-3xl mx-auto leading-relaxed">
            Tell Festiva your occasion, date, guests and budget, and get a complete, editable
            event plan in minutes.
          </p>

          {demoError && (
            <div className="mt-4 max-w-md mx-auto p-3 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300 text-sm">
              {demoError}
            </div>
          )}

          {/* 3 Call-To-Action Buttons */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 max-w-xl mx-auto">
            {/* CTA 1: Try Demo */}
            <button
              type="button"
              onClick={handleTryDemo}
              disabled={demoLoading}
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 hover:brightness-105 active:brightness-95 text-slate-950 font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 shadow-lg shadow-amber-500/25 transition disabled:opacity-50 cursor-pointer"
            >
              {demoLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                  <span>Loading Demo Plan...</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-5 h-5" />
                  <span>Try the demo</span>
                </>
              )}
            </button>

            {/* CTA 2: Create an event */}
            <button
              type="button"
              onClick={handleCreateEvent}
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-950 font-bold text-sm sm:text-base flex items-center justify-center gap-2 transition shadow-md cursor-pointer"
            >
              <Calendar className="w-4 h-4" />
              <span>Create an event</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* CTA 3: Log in */}
            <button
              type="button"
              onClick={onNavigateLogin}
              className="w-full sm:w-auto px-5 py-3.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 font-semibold text-sm sm:text-base transition cursor-pointer"
            >
              Log in
            </button>
          </div>

          {/* Social Proof & Demonstration Highlight Pill */}
          <div className="mt-10 pt-8 border-t border-slate-200/80 dark:border-slate-800/80 flex flex-wrap items-center justify-center gap-y-2 gap-x-6 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Balanced budget allocation (100.0%)
            </span>
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Mangaluru benchmarks & venues
            </span>
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Printable PDF export
            </span>
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              Versioned proposal review
            </span>
          </div>
        </div>
      </section>

      {/* "How It Works" in 3 Steps */}
      <section className="py-16 sm:py-24 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <h2 className="text-xs uppercase tracking-widest text-amber-700 dark:text-amber-400 font-bold mb-2">
              Simple 3-Step Workflow
            </h2>
            <h3 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white font-display">
              From initial thought to a locked-in plan
            </h3>
            <p className="mt-3 text-slate-600 dark:text-slate-400 text-sm sm:text-base">
              Festiva handles mathematical balancing and venue organization so you can focus on the celebration.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="relative rounded-2xl p-6 sm:p-7 border border-slate-200 dark:border-slate-800 bg-stone-50/70 dark:bg-slate-950/50 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-700 dark:text-amber-400 font-bold text-base mb-4">
                  1
                </div>
                <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                  Describe your event
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Enter a brief in plain language or use structured fields for date, guest count,
                  and Mangaluru location.
                </p>
              </div>
              <div className="mt-6 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-700 dark:text-slate-300">
                <span className="text-amber-700 dark:text-amber-400 font-semibold">Example: </span>
                "21st birthday party, Mangaluru, 80 people, ₹75,000, outdoor evening with music"
              </div>
            </div>

            {/* Step 2 */}
            <div className="relative rounded-2xl p-6 sm:p-7 border border-slate-200 dark:border-slate-800 bg-stone-50/70 dark:bg-slate-950/50 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-700 dark:text-amber-400 font-bold text-base mb-4">
                  2
                </div>
                <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                  Review plan & budget
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Festiva generates an itemized budget across venue, catering, decor, and photography,
                  with category shares summing to exactly 100%.
                </p>
              </div>
              <div className="mt-6 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-700 dark:text-slate-300">
                  <span>Food & Beverage</span>
                  <span className="font-semibold text-slate-900 dark:text-white">₹32,000 (42.7%)</span>
                </div>
                <div className="flex justify-between text-slate-700 dark:text-slate-300">
                  <span>Venue Rental</span>
                  <span className="font-semibold text-slate-900 dark:text-white">₹16,250 (21.7%)</span>
                </div>
                <div className="flex justify-between text-emerald-700 dark:text-emerald-400 font-medium pt-1 border-t border-slate-200 dark:border-slate-800">
                  <span>Total Budget</span>
                  <span>₹75,000 (100.0%)</span>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="relative rounded-2xl p-6 sm:p-7 border border-slate-200 dark:border-slate-800 bg-stone-50/70 dark:bg-slate-950/50 flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-700 dark:text-amber-400 font-bold text-base mb-4">
                  3
                </div>
                <h4 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                  Refine with Copilot & export
                </h4>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  Request changes naturally like "reduce décor by ₹10,000 and keep a rain contingency",
                  inspect side-by-side diffs, accept to create v2, and download your PDF.
                </p>
              </div>
              <div className="mt-6 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-semibold">
                  <GitCompare className="w-3.5 h-3.5" />
                  Proposal: Plan v2
                </span>
                <span className="inline-flex items-center gap-1 text-slate-600 dark:text-slate-400">
                  <Download className="w-3.5 h-3.5" />
                  PDF Export
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 sm:py-24 bg-stone-50/60 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <h2 className="text-xs uppercase tracking-widest text-amber-700 dark:text-amber-400 font-bold mb-2">
              Built For Stress-Free Events
            </h2>
            <h3 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white font-display">
              Everything you need to orchestrate a memorable day
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Precision Budget Balancer
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Budget categories stay mathematically balanced. Shares always sum to 100%, amounts match
                your total, and funds reallocate cleanly to named contingencies.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <Clock className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Structured Timeline & Tasks
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Actionable milestones mapped from months before the date down to day-of run-of-show
                schedules with designated responsible roles.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <CheckSquare className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Vendor Checklist & Questions
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Curated categories with tailored negotiation questions for venue coordinators,
                caterers, and decorators before you commit.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <GitCompare className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Plan Versions with Diff View
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Every refinement is previewed as a side-by-side proposal. Accepting creates Plan vN+1;
                rejecting preserves your current plan untouched.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <Mail className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Vendor Inquiry Drafter
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Generate professional inquiry emails grounded in your event date, headcount, and budget
                ready to copy into WhatsApp or email.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="rounded-2xl p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white mb-2">
                Printable PDF Export
              </h4>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                Export high-resolution, print-ready documents with correct Indian Rupee (₹) formatting,
                balanced budget tables, and execution timelines.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Demonstration Data & Transparency Notice */}
      <section className="py-10 bg-amber-500/5 dark:bg-amber-500/10 border-b border-amber-500/20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center sm:text-left flex flex-col sm:flex-row items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-6 h-6 text-amber-700 dark:text-amber-400" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Demonstration Data Disclosure
            </h4>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
              Vendor directories and pricing data are sample demonstration datasets grounded in
              Mangaluru event benchmarks. All sample listings are clearly labeled to keep simulations
              transparent.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom CTA Banner */}
      <section className="py-14 sm:py-20 bg-white dark:bg-slate-900 text-center border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h3 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white font-display mb-3">
            Ready to plan your next Mangaluru celebration?
          </h3>
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-xl mx-auto mb-8">
            Experience the interactive demo in one click or sign up to create your own event plan.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleTryDemo}
              disabled={demoLoading}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-amber-500 via-amber-400 to-orange-500 hover:brightness-105 active:brightness-95 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-amber-500/20 transition cursor-pointer"
            >
              <PlayCircle className="w-4 h-4" />
              <span>Try the demo</span>
            </button>
            <button
              type="button"
              onClick={handleCreateEvent}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-950 font-bold text-sm flex items-center justify-center gap-2 transition cursor-pointer"
            >
              <span>Create an event</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 bg-slate-100 dark:bg-slate-950 text-slate-600 dark:text-slate-400 text-xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6 text-center sm:text-left">
          <div>
            <div className="flex items-center justify-center sm:justify-start gap-2 mb-1.5">
              <span className="font-bold text-slate-900 dark:text-slate-100 text-sm">Festiva</span>
              <span>— Celebration & Event Planning Copilot</span>
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Built with <span className="font-semibold text-slate-700 dark:text-slate-300">Google Antigravity</span>
            </p>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/11DDBOY11/Festiva"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 transition font-medium"
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
              </svg>
              <span>GitHub Repository</span>
            </a>
            <button
              type="button"
              onClick={onNavigateLogin}
              className="text-slate-700 dark:text-slate-300 hover:text-amber-600 dark:hover:text-amber-400 transition font-medium cursor-pointer"
            >
              Sign In
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};
