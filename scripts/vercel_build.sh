#!/usr/bin/env bash
# Build the React app into ./public for Vercel CDN static hosting.
set -euo pipefail

echo "Installing frontend dependencies..."
cd frontend
npm install
echo "Building frontend..."
npm run build
cd ..

echo "Publishing static assets to public/..."
rm -rf public
mkdir -p public
cp -R frontend/dist/. public/

echo "Vercel frontend build complete."
