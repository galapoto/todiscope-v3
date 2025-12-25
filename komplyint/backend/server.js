/**
 * This backend supports the KOMPLYINT public website only.
 * It intentionally exposes minimal read-only endpoints.
 */

const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 8600;

// CORS configuration - allow only localhost:3600
const corsOptions = {
  origin: 'http://localhost:3600',
  optionsSuccessStatus: 200
};

app.use(cors(corsOptions));

// Minimal request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
  });
  
  next();
});

// Health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Version endpoint
app.get('/version', (req, res) => {
  res.json({
    name: 'KOMPLYINT OY Website API',
    environment: 'development',
    timestamp: new Date().toISOString()
  });
});

// Company endpoint
app.get('/company', (req, res) => {
  res.json({
    name: 'KOMPLYINT OY',
    description: 'Compliance readiness support company',
    email: 'komplyint@komplying.com',
    disclaimer: 'We do not provide legal advice.'
  });
});

// Pages endpoint
app.get('/pages', (req, res) => {
  res.json({
    pages: [
      'home',
      'what-we-do',
      'who-we-are',
      'contact',
      'privacy',
      'terms',
      'cookies'
    ]
  });
});

// i18n endpoint
app.get('/i18n', (req, res) => {
  res.json({
    supported: ['en', 'fi'],
    default: 'en'
  });
});

// Meta endpoint
app.get('/meta', (req, res) => {
  res.json({
    company: 'KOMPLYINT OY',
    title: 'KOMPLYINT — Compliance readiness',
    description: 'Compliance readiness support for organisations',
    email: 'komplyint@komplying.com'
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

