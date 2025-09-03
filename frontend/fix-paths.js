import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const distDir = path.join(__dirname, 'dist');

// Function to fix paths in HTML files
function fixPaths(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Fix absolute paths to relative
  content = content.replace(/href="\/assets\//g, 'href="./assets/');
  content = content.replace(/src="\/assets\//g, 'src="./assets/');
  content = content.replace(/href="\/([^"]+\.html)"/g, 'href="./$1"');
  content = content.replace(/href="\/"/g, 'href="./index.html"');
  
  fs.writeFileSync(filePath, content, 'utf8');
  console.log(`Fixed paths in: ${path.basename(filePath)}`);
}

// Fix all HTML files in dist
const htmlFiles = fs.readdirSync(distDir)
  .filter(file => file.endsWith('.html'))
  .map(file => path.join(distDir, file));

htmlFiles.forEach(fixPaths);

console.log('✅ All paths fixed!');