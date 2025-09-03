#!/usr/bin/env node

/**
 * Test script to verify frontend refactoring
 */

const fs = require('fs');
const path = require('path');

console.log('================================');
console.log('FRONTEND REFACTORING TEST');
console.log('================================\n');

let errors = [];
let warnings = [];

// Test 1: Check removed files don't exist
console.log('1. Checking removed files...');
const removedFiles = [
  'src/js/admin-old.js',
  'src/js/config.prod.js',
  'public/admin-old.html'
];

removedFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    errors.push(`❌ File still exists: ${file}`);
  } else {
    console.log(`   ✅ Removed: ${file}`);
  }
});

// Test 2: Check no references to removed files
console.log('\n2. Checking for references to removed files...');
const jsFiles = [
  'src/js/api.js',
  'src/js/chat.js',
  'src/js/admin.js',
  'src/js/auth.js',
  'src/js/authGuard.js',
  'src/js/components.js',
  'src/js/utils.js'
];

jsFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // Check for references to removed files
    if (content.includes('admin-old')) {
      errors.push(`❌ ${file} still references admin-old`);
    }
    if (content.includes('config.prod')) {
      errors.push(`❌ ${file} still references config.prod`);
    }
    
    // Check for direct fetch calls (should use api.js)
    if (file === 'src/js/chat.js') {
      // Check that chat.js imports api
      if (!content.includes("import api from './api.js'")) {
        warnings.push(`⚠️  ${file} doesn't import api.js`);
      }
      
      // Check for any remaining direct fetch calls to API endpoints
      const fetchPattern = /fetch\s*\(\s*[`'"]\$\{API_BASE_URL\}/g;
      if (fetchPattern.test(content)) {
        warnings.push(`⚠️  ${file} might still have direct API fetch calls`);
      }
    }
  }
});

// Test 3: Check API service completeness
console.log('\n3. Checking API service...');
const apiPath = path.join(__dirname, 'src/js/api.js');
if (fs.existsSync(apiPath)) {
  const apiContent = fs.readFileSync(apiPath, 'utf8');
  
  const requiredMethods = [
    'sendMessage',
    'getDocuments',
    'uploadDocuments',
    'deleteDocument',
    'checkHealth',
    'getSessions',
    'getStats'
  ];
  
  requiredMethods.forEach(method => {
    if (apiContent.includes(`async ${method}`)) {
      console.log(`   ✅ API method exists: ${method}`);
    } else {
      warnings.push(`⚠️  API method might be missing: ${method}`);
    }
  });
}

// Test 4: Check configuration
console.log('\n4. Checking configuration...');
const configPath = path.join(__dirname, 'src/js/config.js');
if (fs.existsSync(configPath)) {
  const configContent = fs.readFileSync(configPath, 'utf8');
  
  // Check for environment detection
  if (configContent.includes('window.location.hostname')) {
    console.log('   ✅ Environment detection present');
  } else {
    warnings.push('⚠️  No environment detection in config');
  }
  
  // Check for production URL
  if (configContent.includes('run.app')) {
    console.log('   ✅ Production URL configured');
  } else {
    warnings.push('⚠️  Production URL might not be configured');
  }
}

// Test 5: Check HTML files for script references
console.log('\n5. Checking HTML files...');
const htmlFiles = [
  'public/index.html',
  'public/chat.html',
  'public/admin.html'
];

htmlFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  if (fs.existsSync(filePath)) {
    const content = fs.readFileSync(filePath, 'utf8');
    
    if (content.includes('admin-old.js')) {
      errors.push(`❌ ${file} still references admin-old.js`);
    }
    if (content.includes('config.prod.js')) {
      errors.push(`❌ ${file} still references config.prod.js`);
    }
  }
});

// Results
console.log('\n================================');
console.log('TEST RESULTS');
console.log('================================');

if (errors.length === 0 && warnings.length === 0) {
  console.log('\n✅ ALL TESTS PASSED!');
  console.log('Frontend refactoring completed successfully.');
} else {
  if (errors.length > 0) {
    console.log('\n❌ ERRORS:');
    errors.forEach(error => console.log(error));
  }
  
  if (warnings.length > 0) {
    console.log('\n⚠️  WARNINGS:');
    warnings.forEach(warning => console.log(warning));
  }
  
  console.log('\nPlease fix the issues above before proceeding.');
}

console.log('\n================================');
process.exit(errors.length > 0 ? 1 : 0);