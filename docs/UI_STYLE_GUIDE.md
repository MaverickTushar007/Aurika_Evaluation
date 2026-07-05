# Aurika Enterprise UI Style Guide
**Design System & Aesthetics Reference v1.0.0**

## 1. Design Aesthetics & Philosophy
The Aurika dashboard is engineered to evoke a premium, state-of-the-art enterprise aesthetic. It eschews generic layouts in favor of modern glassmorphism, curated HSL color palettes, subtle micro-animations, and Inter typography.

## 2. Color Palette & Dark Mode Tokens
The system utilizes dark slate backgrounds with vibrant emerald and teal accents to maximize visual scannability and contrast during continuous operations monitoring:
- **Background Base**: `#020617` (Tailwind `bg-slate-950`)
- **Card Panels**: `#0f172a / 80% opacity` (`bg-slate-900/80` with `backdrop-blur-md`)
- **Primary Brand Accent**: `#10b981` (`emerald-500`) for normal operational flow and positive confirmations.
- **Warning / Bottlenecks**: `#f59e0b` (`amber-500`) for host queue warnings and medium priority recommendations.
- **Critical / Occupied**: `#f43f5e` (`rose-500`) for active table occupancy, kitchen load spikes, and critical alerts.
- **Relational Intelligence**: `#a855f7` (`purple-500`) for Identity Memory Engine and Global Identity Graph components.

## 3. Typography
- **Primary Font**: `Inter` (Google Fonts), weights `300, 400, 500, 600, 700`.
- **Monospace Telemetry**: Font family `monospace` for IDs, timestamps, UUIDs, coordinates, and real-time FPS metrics.

## 4. Custom Utility Classes (`src/index.css`)
To maintain consistency without ad-hoc class clutter, the dashboard defines reusable CSS utility components:
- `.glass-panel`: Standard container styling featuring backdrop blur, slate borders, and subtle shadow.
- `.glass-card`: Interactive hover card with smooth border transitions.
- `.glass-button`: Premium action button with emerald gradient and active scaling micro-animation.
