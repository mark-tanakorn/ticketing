import React from 'react';

// Map provider types to their simple-icons slugs
const PROVIDER_ICON_MAP: Record<string, { slug: string; hex: string; name: string }> = {
  openai: { slug: 'openai', hex: '412991', name: 'OpenAI' },
  anthropic: { slug: 'anthropic', hex: 'CC9B7A', name: 'Anthropic' },
  deepseek: { slug: 'deepseek', hex: '1A8CFF', name: 'DeepSeek' }, // Fallback if not in simple-icons
  local: { slug: 'ollama', hex: '000000', name: 'Ollama' },
  google: { slug: 'google', hex: '4285F4', name: 'Google' },
  cohere: { slug: 'cohere', hex: 'D18EE2', name: 'Cohere' }, // Fallback if not available
  mistral: { slug: 'mistralai', hex: 'FF7000', name: 'Mistral AI' },
  groq: { slug: 'groq', hex: 'F55036', name: 'Groq' }, // Fallback if not available
  perplexity: { slug: 'perplexity', hex: '20808D', name: 'Perplexity' }, // Fallback if not available
  together: { slug: 'together', hex: '000000', name: 'Together AI' }, // Fallback
  replicate: { slug: 'replicate', hex: '000000', name: 'Replicate' }, // Fallback
  huggingface: { slug: 'huggingface', hex: 'FFD21E', name: 'HuggingFace' },
};

interface ProviderIconProps {
  provider: string;
  size?: number;
  className?: string;
}

export default function ProviderIcon({ provider, size = 32, className = '' }: ProviderIconProps) {
  const iconData = PROVIDER_ICON_MAP[provider.toLowerCase()];
  
  if (!iconData) {
    // Fallback to a generic icon
    return (
      <div 
        className={`flex items-center justify-center rounded-lg ${className}`}
        style={{ 
          width: size, 
          height: size, 
          background: 'var(--theme-surface-variant)',
          color: 'var(--theme-text-muted)'
        }}
      >
        <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </div>
    );
  }

  const { hex } = iconData;
  
  // Use SVG path from simple-icons dynamically
  // For now, we'll use a colored circle as placeholder until we import the actual icons
  return (
    <div 
      className={`flex items-center justify-center rounded-lg ${className}`}
      style={{ 
        width: size, 
        height: size, 
        background: `#${hex}15`, // 15% opacity of brand color
        color: `#${hex}`
      }}
    >
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="currentColor">
        {/* Generic placeholder - will be replaced with actual simple-icons SVG paths */}
        <circle cx="12" cy="12" r="8"/>
      </svg>
    </div>
  );
}

// Export the icon map for use in dropdowns
export { PROVIDER_ICON_MAP };

