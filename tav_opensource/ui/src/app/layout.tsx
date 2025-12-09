"use client";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import NavBar from "../components/NavBar";
import { ThemeProvider } from "../components/ThemeProvider";
import { useState, useEffect, useRef } from "react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Note: metadata cannot be exported from client components
// Next.js will use default metadata or you can set it in a layout.ts file

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const headerRef = useRef<HTMLDivElement | null>(null);
  // Cat animation control (re-add state and refs)
  const [isCatAnimating, setIsCatAnimating] = useState(false);
  const isCatAnimatingRef = useRef(false);
  const catTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (ev: MediaQueryListEvent) => setPrefersReducedMotion(ev.matches);
    setPrefersReducedMotion(mediaQuery.matches);
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    }
    mediaQuery.addListener(handler);
    return () => mediaQuery.removeListener(handler);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const updateVars = () => {
      const headerEl = headerRef.current;
      const logoEl = headerEl?.querySelector<HTMLImageElement>(".cat-logo-img");
      if (!headerEl || !logoEl) return;
      const headerRect = headerEl.getBoundingClientRect();
      const logoRect = logoEl.getBoundingClientRect();
      const paddingLeft = 16; // px - matches px-6 in header div
      const rightPadding = 16;
      const maxTranslate = Math.max(0, headerRect.width - paddingLeft - rightPadding - logoRect.width);
      document.documentElement.style.setProperty("--cat-max-translate", `${Math.round(maxTranslate)}px`);
    };
    updateVars();
    window.addEventListener("resize", updateVars);
    return () => window.removeEventListener("resize", updateVars);
  }, []);

  // --- Cat animation: random 50% chance per second ---
  useEffect(() => {
    if (typeof window === "undefined") return;

    // If user prefers reduced motion, disable the animation logic
    if (prefersReducedMotion) {
      // Clear any timers and ensure animation is off
      if (catTimerRef.current) {
        window.clearTimeout(catTimerRef.current);
        catTimerRef.current = null;
      }
      isCatAnimatingRef.current = false;
      setIsCatAnimating(false);
      return;
    }

    // Interval running every second to attempt start
    const intervalId = window.setInterval(() => {
      // If already animating, do nothing
      if (isCatAnimatingRef.current) return;

      // 90% chance
      if (Math.random() < 0.00001
    ) {
        // Start animation
        setIsCatAnimating(true);
        isCatAnimatingRef.current = true;

        // Disable attempts for the duration (60s)
        catTimerRef.current = window.setTimeout(() => {
          setIsCatAnimating(false);
          isCatAnimatingRef.current = false;
          if (catTimerRef.current) {
            window.clearTimeout(catTimerRef.current);
            catTimerRef.current = null;
          }
        }, 60000);
      }
    }, 10000);

    return () => {
      window.clearInterval(intervalId);
      if (catTimerRef.current) {
        window.clearTimeout(catTimerRef.current);
        catTimerRef.current = null;
      }
    };
  }, [prefersReducedMotion]);

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* FontAwesome Icons */}
        <link 
          rel="stylesheet" 
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" 
          integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA==" 
          crossOrigin="anonymous" 
          referrerPolicy="no-referrer" 
        />
        {/* Prevent flash of wrong theme */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                const savedTheme = localStorage.getItem('theme');
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                const theme = savedTheme || (prefersDark ? 'dark' : 'light');
                
                const root = document.documentElement;
                root.classList.remove('theme-light', 'theme-dark', 'theme-default', 'dark');
                
                if (theme === 'dark') {
                  root.classList.add('theme-dark', 'dark');
                } else if (theme === 'default') {
                  root.classList.add('theme-default');
                } else {
                  root.classList.add('theme-light');
                }
              })();
            `,
          }}
        />
        {/* Prevent cat flashing on left before hydration */}
        {/* <style>{`.cat-logo{transform: translateX(-120px);}`}</style> */}
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased flex flex-col h-screen`}>
        <ThemeProvider>
          <header className="shrink-0 border-b" style={{ background: 'var(--theme-navbar)', borderColor: 'var(--theme-border)' }}>
            <div ref={headerRef} className="flex items-center justify-between px-6 py-4 relative">
              <img src="/images/logo.png" alt="Logo" className="w-25 h-auto mt-3 ml-3 mb-3" />
              <NavBar />

              {/* Animated cat that moves across the header area */}
              <a
                href="/"
                aria-label="Home"
                title="Home"
                // Lift the cat upwards with negative top margin: -mt-3 to -mt-6 can be adjusted as needed
                className="cat-logo absolute left-4 top-full -mt-14 z-30"
                style={!prefersReducedMotion ? (isCatAnimating ? { animation: 'catMove 60s linear 1', transform: 'translateX(-100px)' } : { transform: 'translateX(-120px)' }) : undefined}
              >
                <img src="/images/ezgif-374f00b978ecda9a.gif" alt="TAV logo" className="cat-logo-img h-10 w-10 md:h-20 md:w-20 rounded-full" />
              </a>
              {!prefersReducedMotion && (
                <style>{`
                  @keyframes catMove { 0% { transform: translateX(-100px); } 100% { transform: translateX(calc(var(--cat-max-translate) + 100px)); } }
                  .cat-logo:hover { animation-play-state: paused; }
                `}</style>
              )}
            </div>
          </header>
          <main className="flex-1 overflow-hidden">
            {children}
        </main>
        </ThemeProvider>
      </body>
    </html>
  );
}