# Next.js Frontend Setup

**Status:** ✅ **CORRECT SETUP - Using Next.js**

---

## Important: Use Next.js, Not Vite

The frontend is built with **Next.js 16** and is located in the `frontend/web/` directory.

**DO NOT** use the Vite setup. All development should happen in `frontend/web/`.

---

## Running the Frontend

### Development Server

```bash
cd frontend/web
npm run dev
```

The server will start on:
- **Local:** http://localhost:3000/ (or next available port)
- **Network:** Available on your local network

### Build for Production

```bash
cd frontend/web
npm run build
npm start
```

---

## Project Structure

```
frontend/
├── web/                    ← NEXT.JS APP (USE THIS)
│   ├── src/
│   │   ├── app/           ← Next.js App Router pages
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── dashboard/
│   │   │   ├── reports/
│   │   │   └── providers.tsx
│   │   ├── components/    ← React components
│   │   │   ├── dashboard/
│   │   │   ├── widgets/
│   │   │   ├── ui/
│   │   │   └── layout/
│   │   ├── hooks/         ← Custom React hooks
│   │   ├── lib/           ← Utilities and API client
│   │   └── ...
│   ├── package.json
│   ├── next.config.ts
│   └── ...
└── src/                    ← OLD VITE SETUP (IGNORE/DELETE)
```

---

## Key Features

### ✅ Already Implemented

1. **Next.js 16** with App Router
2. **React 19** 
3. **TypeScript**
4. **Tailwind CSS 4**
5. **i18next** for multilingual support (8 languages)
6. **React Query** for data fetching
7. **React Grid Layout** for draggable/resizable widgets
8. **Recharts** for data visualization
9. **Theme system** (light/dark mode)
10. **Authentication** context
11. **Dataset** context
12. **API client** with proper error handling

### Components Available

- **Dashboard Grid** - Draggable/resizable widget system
- **Widget Shell** - Reusable widget wrapper
- **Report Builder** - AI report generation
- **Dataset Table** - Dataset management
- **UI Components** - Button, Card, Modal, etc.
- **Layout Components** - AppShell, Navigation

---

## API Configuration

The API client is configured in `frontend/web/src/lib/api-client.ts`:

- **Base URL:** `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8400`)
- **API Key:** `NEXT_PUBLIC_API_KEY` (from environment variables)

### Environment Variables

Create a `.env.local` file in `frontend/web/`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8400
NEXT_PUBLIC_API_KEY=your-api-key-here
```

---

## Widget System

The dashboard uses `react-grid-layout` for a draggable/resizable widget system:

- Widgets are stored in `localStorage`
- Layouts are responsive (lg, md, sm, xs breakpoints)
- Widgets can be pinned, moved, resized, and removed
- Keyboard navigation supported

### Adding New Widgets

1. Create widget component in `src/components/widgets/`
2. Add to `initialWidgets` in `src/components/dashboard/dashboard-grid.tsx`
3. Add layout configuration to `baseLayout`

---

## Internationalization

i18next is configured with 8 languages:
- Finnish (fi) - Default
- English (en)
- Swedish (sv)
- German (de)
- Dutch (nl)
- French (fr)
- Spanish (es)
- Chinese Mandarin (zh)

Translations are in `src/lib/i18n.ts` (inline) or can be moved to JSON files.

---

## Development Workflow

1. **Start Backend:**
   ```bash
   cd backend
   uvicorn backend.app.main:app --reload --port 8400
   ```

2. **Start Frontend:**
   ```bash
   cd frontend/web
   npm run dev
   ```

3. **Access Application:**
   - Open http://localhost:3000 (or port shown in terminal)
   - Navigate to Dashboard, Reports, etc.

---

## Troubleshooting

### Port Already in Use

If port 3000 is in use, Next.js will automatically use the next available port (3001, 3002, etc.)

### Lock File Error

If you see "Unable to acquire lock", another Next.js dev server is running:
```bash
# Kill the process
pkill -f "next dev"
# Or find and kill manually
lsof -ti:3000 | xargs kill
```

### Blank Page

1. Check browser console for errors
2. Verify backend is running on port 8400
3. Check API configuration in `.env.local`
4. Verify all dependencies are installed: `npm install`

---

## Dependencies

All dependencies are in `frontend/web/package.json`:

- **Next.js 16.0.6**
- **React 19.2.3**
- **TypeScript 5**
- **Tailwind CSS 4**
- **React Query 5.90.12**
- **i18next 25.7.3**
- **react-grid-layout 2.1.1**
- **Recharts 3.6.0**
- **xlsx 0.18.5**
- And more...

---

## Next Steps

1. ✅ Next.js is set up and running
2. ✅ All core components are in place
3. ✅ Widget system is functional
4. ✅ API client is configured
5. ✅ i18n is configured

**The frontend is ready for development!**

---

**Remember:** Always work in `frontend/web/`, not in the root `frontend/` directory.





