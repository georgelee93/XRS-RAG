#!/usr/bin/env node

/**
 * Post-build script to fix inline module scripts
 * Vite removes inline module scripts, so we need to preserve them
 */

const fs = require('fs');
const path = require('path');

const htmlFiles = [
  'admin.html',
  'chat.html', 
  'login.html',
  'signup.html'
];

const distDir = path.join(__dirname, '..', 'dist');
const publicDir = path.join(__dirname, '..', 'public');

console.log('Fixing inline scripts in built HTML files...');

htmlFiles.forEach(file => {
  const distPath = path.join(distDir, file);
  const publicPath = path.join(publicDir, file);
  
  if (!fs.existsSync(distPath)) {
    console.warn(`Warning: ${file} not found in dist`);
    return;
  }
  
  // Read the original file to get inline scripts
  const originalContent = fs.readFileSync(publicPath, 'utf8');
  const distContent = fs.readFileSync(distPath, 'utf8');
  
  // Extract inline module scripts from original
  const scriptRegex = /<script type="module">([\s\S]*?)<\/script>/g;
  const inlineScripts = [];
  let match;
  
  while ((match = scriptRegex.exec(originalContent)) !== null) {
    inlineScripts.push(match[0]);
  }
  
  if (inlineScripts.length > 0) {
    // Find where to insert scripts (before closing body tag)
    const bodyCloseIndex = distContent.lastIndexOf('</body>');
    
    if (bodyCloseIndex !== -1) {
      // Insert the inline scripts
      const newContent = 
        distContent.slice(0, bodyCloseIndex) + 
        '\n' + inlineScripts.join('\n') + '\n' +
        distContent.slice(bodyCloseIndex);
      
      // Write the updated content
      fs.writeFileSync(distPath, newContent);
      console.log(`✓ Fixed ${file} - restored ${inlineScripts.length} inline script(s)`);
    }
  }
});

console.log('Build fix complete!');