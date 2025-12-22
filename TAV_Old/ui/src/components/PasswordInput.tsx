/**
 * PasswordInput Component
 * 
 * A reusable password input with show/hide toggle (eye icon).
 * Applies consistent styling with theme support.
 */

import { useState } from 'react';

interface PasswordInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  autoComplete?: string;
}

export default function PasswordInput({
  value,
  onChange,
  placeholder = "Enter password or API key",
  disabled = false,
  className = "",
  autoComplete = "off"
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="relative">
      <input
        type={showPassword ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={autoComplete}
        className={`w-full border rounded-lg px-4 py-2 pr-12 focus:outline-none ${className}`}
        style={{
          background: "var(--theme-surface-variant)",
          borderColor: "var(--theme-border)",
          color: "var(--theme-text)",
        }}
        onFocus={(e) =>
          (e.currentTarget.style.borderColor = "var(--theme-primary)")
        }
        onBlur={(e) =>
          (e.currentTarget.style.borderColor = "var(--theme-border)")
        }
      />
      <button
        type="button"
        onClick={() => setShowPassword(!showPassword)}
        disabled={disabled}
        className="absolute right-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
        style={{
          color: showPassword ? "var(--theme-primary)" : "var(--theme-text-muted)",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
        }}
        title={showPassword ? "Hide" : "Show"}
      >
        {showPassword ? (
          // Eye slash (hide)
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
            <line x1="1" y1="1" x2="23" y2="23" />
          </svg>
        ) : (
          // Eye (show)
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}

