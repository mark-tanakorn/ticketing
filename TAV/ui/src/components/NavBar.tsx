"use client";
import { usePathname } from "next/navigation";

const navLinks = [
  { 
    name: "Dashboard", 
    href: "/",
    icon: (
      <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
      </svg>
    )
  },
  { 
    name: "Editor", 
    href: "/editor-page",
    icon: (
      <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20h9"/>
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
      </svg>
    )
  },
  { 
    name: "Settings", 
    href: "/settings-page",
    icon: (
      <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    )
  },
];

export default function NavBar() {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1">
      {navLinks.map((link) => {
        const isActive =
          link.href === "/"
            ? pathname === "/"
            : pathname.startsWith(link.href);
        return (
          <a
            key={link.name}
            href={link.href}
            className="flex items-center gap-2 px-5 py-2 rounded-xl text-xl font-bold transition-all duration-200"
            style={{ 
              color: 'var(--theme-text)',
              background: isActive ? 'var(--theme-surface-hover)' : 'transparent',
              boxShadow: isActive ? '0 2px 10px rgba(0,0,0,0.15)' : 'none',
              opacity: isActive ? 1 : 0.7,
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.background = 'var(--theme-surface-hover)';
                e.currentTarget.style.opacity = '0.9';
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive) {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.opacity = '0.7';
              }
            }}
          >
            <span style={{ opacity: isActive ? 1 : 0.7 }}>
              {link.icon}
            </span>
            {link.name}
          </a>
        );
      })}
    </nav>
  );
}