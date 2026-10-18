import React from 'react';

interface ShieldLogoProps {
  className?: string;
  size?: number;
  showText?: boolean;
}

export const ShieldLogo: React.FC<ShieldLogoProps> = ({
  className = '',
  size = 38,
  showText = false
}) => {
  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      <div 
        className="relative flex items-center justify-center shrink-0 rounded-lg overflow-hidden"
        style={{ width: size, height: size }}
      >
        <svg
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full drop-shadow-[0_0_14px_rgba(0,180,255,0.45)]"
        >
          <defs>
            {/* Ambient Dark Canvas Background */}
            <radialGradient id="logoBgGrad" cx="50%" cy="45%" r="65%">
              <stop offset="0%" stopColor="#081528" />
              <stop offset="70%" stopColor="#030712" />
              <stop offset="100%" stopColor="#01040a" />
            </radialGradient>

            {/* Neon Shield Stroke Gradient */}
            <linearGradient id="shieldBorderGrad" x1="50" y1="8" x2="50" y2="92" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#67e8f9" />
              <stop offset="25%" stopColor="#38bdf8" />
              <stop offset="75%" stopColor="#0284c7" />
              <stop offset="100%" stopColor="#0369a1" />
            </linearGradient>

            {/* Robot Head Body Gradient */}
            <linearGradient id="robotBodyGrad" x1="50" y1="30" x2="50" y2="65" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="50%" stopColor="#0ea5e9" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>

            {/* Ear Muffs Gradient */}
            <linearGradient id="muffGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0369a1" />
            </linearGradient>

            {/* Neon Eye Glow Filter */}
            <filter id="eyeGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Shield Outline Glow Filter */}
            <filter id="shieldGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Deep Navy/Black Background Rounded Box */}
          <rect width="100" height="100" rx="18" fill="url(#logoBgGrad)" />

          {/* Glowing Outer Shield Path */}
          <path
            d="M 50 11 C 67 15, 82 19, 83 24 L 83 49 C 83 67, 68 81, 50 88 C 32 81, 17 67, 17 49 L 17 24 C 18 19, 33 15, 50 11 Z"
            fill="#030914"
            stroke="url(#shieldBorderGrad)"
            strokeWidth="4.2"
            strokeLinejoin="round"
            filter="url(#shieldGlow)"
          />

          {/* Crisp Shield Inner Stroke */}
          <path
            d="M 50 11 C 67 15, 82 19, 83 24 L 83 49 C 83 67, 68 81, 50 88 C 32 81, 17 67, 17 49 L 17 24 C 18 19, 33 15, 50 11 Z"
            fill="none"
            stroke="#e0f2fe"
            strokeWidth="0.8"
            strokeOpacity="0.4"
          />

          {/* Orbital Pulse Pills / Radiation Ticks */}
          {/* Top Pill */}
          <rect x="48.5" y="23" width="3" height="5.5" rx="1.5" fill="#38bdf8" />
          
          {/* Bottom Pill */}
          <rect x="48.5" y="66.5" width="3" height="5.5" rx="1.5" fill="#0284c7" />

          {/* Top-Left Angled Pill */}
          <g transform="translate(31, 32) rotate(-45)">
            <rect x="-1.5" y="-3" width="3" height="6" rx="1.5" fill="#38bdf8" />
          </g>

          {/* Top-Right Angled Pill */}
          <g transform="translate(69, 32) rotate(45)">
            <rect x="-1.5" y="-3" width="3" height="6" rx="1.5" fill="#38bdf8" />
          </g>

          {/* Small Lower-Right Status Dot/Pill */}
          <rect x="65" y="58" width="2.5" height="4.5" rx="1.25" fill="#38bdf8" />

          {/* Robot Side Ear Muffs */}
          {/* Left Ear Muff */}
          <rect x="30" y="43" width="4.8" height="10" rx="2.4" fill="url(#muffGrad)" />
          {/* Right Ear Muff */}
          <rect x="65.2" y="43" width="4.8" height="10" rx="2.4" fill="url(#muffGrad)" />

          {/* Main Robot Head & Torso Silhouette */}
          <path
            d="M 34 43.5 
               C 34 32, 66 32, 66 43.5 
               C 66 49.5, 63.5 52.5, 61.5 55 
               C 63.5 59, 64 63, 63.5 64.5 
               C 58 65.5, 42 65.5, 36.5 64.5 
               C 36 63, 36.5 59, 38.5 55 
               C 36.5 52.5, 34 49.5, 34 43.5 Z"
            fill="url(#robotBodyGrad)"
          />

          {/* Inner Curved Visor (Dark Mask) */}
          <rect 
            x="36.5" 
            y="38.5" 
            width="27" 
            height="15" 
            rx="5.5" 
            fill="#030712" 
            stroke="#0284c7" 
            strokeWidth="0.8" 
          />

          {/* Glowing Cyan Robot Eyes inside Visor */}
          {/* Left Eye */}
          <path
            d="M 41.8 43.8 C 43.2 43.8, 44.8 44.8, 44.8 47.4 C 43.2 48.0, 41.8 46.8, 41.8 43.8 Z"
            fill="#22d3ee"
            filter="url(#eyeGlow)"
          />

          {/* Right Eye */}
          <path
            d="M 58.2 43.8 C 56.8 43.8, 55.2 44.8, 55.2 47.4 C 56.8 48.0, 58.2 46.8, 58.2 43.8 Z"
            fill="#22d3ee"
            filter="url(#eyeGlow)"
          />
        </svg>
      </div>

      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 leading-none">
            <span className="text-base font-bold tracking-tight text-white font-sans">
              RoboIQ <span className="text-cyan-400">Guardian</span>
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-sans tracking-tight mt-0.5">
            Embodied Intelligence for Robotic Recovery
          </span>
        </div>
      )}
    </div>
  );
};
