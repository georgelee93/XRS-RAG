#!/usr/bin/env node

import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.resolve(__dirname, '../dist');
const publicDir = path.join(distDir, 'public');

async function moveHtmlFiles() {
  try {
    // Check if public directory exists
    const publicExists = await fs.access(publicDir).then(() => true).catch(() => false);
    
    if (publicExists) {
      // Get all HTML files from dist/public
      const files = await fs.readdir(publicDir);
      const htmlFiles = files.filter(file => file.endsWith('.html'));
      
      // Move each HTML file to dist root
      for (const file of htmlFiles) {
        const source = path.join(publicDir, file);
        const dest = path.join(distDir, file);
        
        console.log(`Moving ${file} to dist root...`);
        await fs.rename(source, dest);
      }
      
      // Remove the now-empty public directory
      await fs.rmdir(publicDir);
      console.log('Post-build cleanup complete!');
    }
  } catch (error) {
    console.error('Post-build error:', error);
    process.exit(1);
  }
}

moveHtmlFiles();