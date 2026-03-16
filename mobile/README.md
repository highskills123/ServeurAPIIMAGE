# PixelForge AI — Mobile & Web Client

A React Native (Expo) app that connects to the [PixelForge AI API](../README.md) backend to generate images from text prompts.

The **same codebase** runs as:

- 📱 **Android app** — publishable to the Google Play Store
- 🌐 **Web app** — deployable to any static hosting service

---

## Features

| Screen | Description |
|--------|-------------|
| **Login / Sign Up** | JWT-based authentication |
| **Create** | Enter a text prompt, choose dimensions & steps, and generate AI images |
| **Gallery** | Browse all previously generated images |
| **Profile** | View account info and sign out |

---

## Requirements

- [Node.js](https://nodejs.org/) ≥ 18
- [Expo CLI](https://docs.expo.dev/get-started/installation/) — `npm install -g expo-cli`
- For Android builds: [EAS CLI](https://docs.expo.dev/eas/) — `npm install -g eas-cli`

---

## Quick Start (Development)

```bash
# 1. Install dependencies
cd mobile
npm install

# 2. Copy the env file and set your backend URL
cp .env.example .env
# Edit .env and set EXPO_PUBLIC_API_URL to your backend address
# e.g. EXPO_PUBLIC_API_URL=http://192.168.1.100:80

# 3. Start the dev server
npm start
# Then press:
#   a  → open on Android emulator / device
#   w  → open in web browser
```

---

## 🌐 Deploy as a Website

### Option A – Export to static files (host anywhere)

```bash
npm run export:web
# Output goes to dist/

# Upload the dist/ folder to any static host:
# - Vercel: vercel deploy dist/
# - Netlify: netlify deploy --dir dist/
# - GitHub Pages, AWS S3, Cloudflare Pages, etc.
```

### Option B – Vercel (one command)

```bash
npm install -g vercel
npm run export:web
vercel dist/
```

> **Note:** Set the `EXPO_PUBLIC_API_URL` environment variable in your hosting
> provider's dashboard to point to your live backend URL before deploying.

---

## 📱 Build for Google Play Store

### 1. Create an Expo account and log in

```bash
npx eas-cli login
```

### 2. Configure your project ID

```bash
npx eas-cli init
```

This replaces the `"YOUR_EAS_PROJECT_ID"` placeholder in `app.json` → `extra.eas.projectId` with your real project ID.
> ⚠️ **Required before running any `eas build` command.** Without this, builds will fail.

### 3. Set your backend URL for production

In `app.json`, you can hardcode the production URL, or pass it via EAS build environment:

```json
"extra": {
  "apiUrl": "https://your-domain.com"
}
```

Or update `src/api.ts` directly to set `API_BASE_URL` to your production server.

### 4. Build an APK (for testing / sideloading)

```bash
npm run build:android:apk
# → Downloads a .apk file you can install directly on a device
```

### 5. Build an AAB (for Google Play Store)

```bash
npm run build:android
# → Downloads a .aab file for Play Store upload
```

### 6. Submit to Google Play

```bash
# First-time setup: create a Google Play service account JSON key
# See: https://docs.expo.dev/submit/android/

npx eas-cli submit --platform android
```

---

## Project Structure

```
mobile/
├── App.tsx                  # Root component with navigation + auth gate
├── app.json                 # Expo app configuration
├── eas.json                 # EAS Build profiles (APK / AAB / preview)
├── src/
│   ├── api.ts               # REST API client (all backend calls)
│   ├── context/
│   │   └── AuthContext.tsx  # Auth state + JWT storage
│   └── screens/
│       ├── LoginScreen.tsx
│       ├── SignupScreen.tsx
│       ├── GenerateScreen.tsx   # Text-to-image generation
│       ├── GalleryScreen.tsx    # Past images grid
│       └── ProfileScreen.tsx    # User info + logout
└── assets/                  # App icons, splash screen
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPO_PUBLIC_API_URL` | `http://localhost:80` | URL of the PixelForge AI backend |

Copy `.env.example` to `.env` and set the value before running.

---

## Troubleshooting

**Cannot connect to backend on device:**
- Make sure `EXPO_PUBLIC_API_URL` uses your machine's local IP (e.g. `192.168.x.x`), not `localhost`.
- Both your phone and computer must be on the same Wi-Fi network during development.

**Images not loading:**
- The backend serves images at `/files/images/...`. Ensure Nginx is running (`docker-compose up`).

**Build fails with "project ID not found":**
- Run `npx eas-cli init` to link the project to your Expo account.
