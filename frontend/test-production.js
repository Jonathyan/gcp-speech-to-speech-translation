/**
 * Production Configuration Test
 * Validates that the production build is correctly configured for Cloud Run integration
 */

const fs = require('fs');
const path = require('path');

console.log('🧪 Testing Production Configuration...\n');

// Test 1: Verify build output exists
console.log('1. Verifying build output files...');
const requiredFiles = [
  'dist/index.html',
  'dist/app.min.js',
  'dist/styles.css'
];

let allFilesExist = true;
for (const file of requiredFiles) {
  if (fs.existsSync(file)) {
    console.log(`   ✅ ${file} exists`);
  } else {
    console.log(`   ❌ ${file} missing`);
    allFilesExist = false;
  }
}

if (!allFilesExist) {
  console.log('\n❌ Build output incomplete. Run: npm run build');
  process.exit(1);
}

// Test 2: Verify Cloud Run URL configuration
console.log('\n2. Verifying Cloud Run configuration...');
try {
  const appJs = fs.readFileSync('dist/app.min.js', 'utf8');
  
  if (appJs.includes('hybrid-stt-service-ysw2dobxea-ew.a.run.app')) {
    console.log('   ✅ Cloud Run URL found in production build');
  } else {
    console.log('   ❌ Cloud Run URL not found in production build');
    console.log('   Expected: hybrid-stt-service-ysw2dobxea-ew.a.run.app');
    process.exit(1);
  }
  
  if (appJs.includes('wss://')) {
    console.log('   ✅ Secure WebSocket (wss://) configuration found');
  } else {
    console.log('   ❌ Secure WebSocket configuration not found');
    process.exit(1);
  }
  
} catch (error) {
  console.log('   ❌ Failed to read production JavaScript');
  console.log('   Error:', error.message);
  process.exit(1);
}

// Test 3: Verify Firebase configuration
console.log('\n3. Verifying Firebase configuration...');
if (fs.existsSync('firebase.json')) {
  console.log('   ✅ firebase.json exists');
  
  try {
    const firebaseConfig = JSON.parse(fs.readFileSync('firebase.json', 'utf8'));
    
    if (firebaseConfig.hosting && firebaseConfig.hosting.public === 'dist') {
      console.log('   ✅ Firebase hosting configured for dist/ directory');
    } else {
      console.log('   ❌ Firebase hosting not configured correctly');
      process.exit(1);
    }
    
    if (firebaseConfig.hosting.rewrites && firebaseConfig.hosting.rewrites.length > 0) {
      console.log('   ✅ Firebase rewrites configured for SPA');
    } else {
      console.log('   ❌ Firebase rewrites not configured');
    }
    
    if (firebaseConfig.hosting.headers && firebaseConfig.hosting.headers.length > 0) {
      console.log('   ✅ Firebase security headers configured');
    } else {
      console.log('   ⚠️  Firebase security headers not configured');
    }
    
  } catch (error) {
    console.log('   ❌ Failed to parse firebase.json');
    console.log('   Error:', error.message);
    process.exit(1);
  }
} else {
  console.log('   ❌ firebase.json missing');
  process.exit(1);
}

if (fs.existsSync('.firebaserc')) {
  console.log('   ✅ .firebaserc exists');
  
  try {
    const firebaseRc = JSON.parse(fs.readFileSync('.firebaserc', 'utf8'));
    if (firebaseRc.projects && firebaseRc.projects.default === 'lfhs-translate') {
      console.log('   ✅ Firebase project set to lfhs-translate');
    } else {
      console.log('   ❌ Firebase project not configured correctly');
      process.exit(1);
    }
  } catch (error) {
    console.log('   ❌ Failed to parse .firebaserc');
    process.exit(1);
  }
} else {
  console.log('   ❌ .firebaserc missing');
  process.exit(1);
}

// Test 4: Verify HTML structure
console.log('\n4. Verifying HTML structure...');
try {
  const html = fs.readFileSync('dist/index.html', 'utf8');
  
  if (html.includes('Live Speech Translation')) {
    console.log('   ✅ HTML title found');
  } else {
    console.log('   ❌ HTML title not found');
  }
  
  if (html.includes('app.min.js')) {
    console.log('   ✅ Minified JavaScript referenced');
  } else {
    console.log('   ❌ Minified JavaScript not referenced');
  }
  
  // Check for essential UI elements
  const requiredElements = [
    'start-broadcast',
    'join-listener', 
    'stream-id',
    'status'
  ];
  
  let allElementsFound = true;
  for (const elementId of requiredElements) {
    if (html.includes(`id="${elementId}"`)) {
      console.log(`   ✅ UI element #${elementId} found`);
    } else {
      console.log(`   ❌ UI element #${elementId} missing`);
      allElementsFound = false;
    }
  }
  
  if (!allElementsFound) {
    console.log('   ⚠️  Some UI elements are missing - functionality may be impacted');
  }
  
} catch (error) {
  console.log('   ❌ Failed to read HTML file');
  process.exit(1);
}

// Test 5: Check file sizes
console.log('\n5. Checking production file sizes...');
try {
  const stats = {
    'dist/index.html': fs.statSync('dist/index.html').size,
    'dist/app.min.js': fs.statSync('dist/app.min.js').size,
    'dist/styles.css': fs.statSync('dist/styles.css').size
  };
  
  for (const [file, size] of Object.entries(stats)) {
    const sizeKB = (size / 1024).toFixed(1);
    console.log(`   📁 ${file}: ${sizeKB}KB`);
    
    // Warn about large files
    if (file.includes('.js') && size > 500 * 1024) {
      console.log(`   ⚠️  ${file} is large (${sizeKB}KB) - consider optimization`);
    }
  }
  
} catch (error) {
  console.log('   ❌ Failed to check file sizes');
  console.log('   Error:', error.message);
}

// Test Summary
console.log('\n✅ Production Configuration Tests Passed!\n');
console.log('🚀 Ready for Firebase deployment:');
console.log('   1. Ensure you are logged in: firebase login');
console.log('   2. Deploy: ./deploy-firebase.sh');
console.log('   3. Test: Visit the deployed URL and test speaker/listener functionality');
console.log('\n📊 Expected endpoints after deployment:');
console.log('   Frontend: https://lfhs-translate.firebaseapp.com');
console.log('   Backend:  https://hybrid-stt-service-ysw2dobxea-ew.a.run.app');
console.log('   Speaker WebSocket:  wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/speak/{stream_id}');
console.log('   Listener WebSocket: wss://hybrid-stt-service-ysw2dobxea-ew.a.run.app/ws/listen/{stream_id}');
console.log('');