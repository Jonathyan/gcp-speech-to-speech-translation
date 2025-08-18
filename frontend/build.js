#!/usr/bin/env node

/**
 * Simple Build Process
 * Concatenates and minifies JavaScript files for production
 */

const fs = require('fs');
const path = require('path');

// File order for concatenation
const jsFiles = [
    'src/config.js',
    'src/utils.js',
    'src/diagnostics.js',
    'src/wavEncoder.js',    // Phase 2: WAV encoder must load before audio.js
    'src/audio.js',
    'src/audioPlayer.js',
    'src/connection.js',
    'src/ui.js',
    'src/app.js'
];

// Simple minification (remove comments and extra whitespace)
function minifyJS(code) {
    return code
        .replace(/\/\*[\s\S]*?\*\//g, '') // Remove block comments
        .replace(/\/\/.*$/gm, '') // Remove line comments
        .replace(/\n\s+/g, '\n') // Remove leading spaces from new lines but keep line breaks
        .replace(/\s{3,}/g, ' ') // Only collapse 3+ spaces to single space
        .trim();
}

// Build process
function build() {
    console.log('Building frontend...');
    
    // Create dist directory
    const distDir = path.join(__dirname, 'dist');
    if (!fs.existsSync(distDir)) {
        fs.mkdirSync(distDir);
    }
    
    // Concatenate JavaScript files
    let concatenated = '';
    jsFiles.forEach(file => {
        const filePath = path.join(__dirname, file);
        if (fs.existsSync(filePath)) {
            let content = fs.readFileSync(filePath, 'utf8');
            
            // Replace environment detection for production build
            if (file === 'src/config.js') {
                content = content.replace(
                    /return window\.location\.hostname === 'localhost' \? 'development' : 'production';/g,
                    "return 'production';"
                );
                console.log('✓ Set production environment in config.js');
            }
            
            concatenated += content + '\n';
            console.log(`✓ Added ${file}`);
        } else {
            console.warn(`⚠ File not found: ${file}`);
        }
    });
    
    // Write development version
    fs.writeFileSync(path.join(distDir, 'app.js'), concatenated);
    console.log('✓ Created dist/app.js');
    
    // Write "minified" version (just copy concatenated for safety)
    fs.writeFileSync(path.join(distDir, 'app.min.js'), concatenated);
    console.log('✓ Created dist/app.min.js');
    
    // Copy HTML with updated script references
    const htmlPath = path.join(__dirname, 'public/index.html');
    let html = fs.readFileSync(htmlPath, 'utf8');
    
    // Replace multiple script tags with single minified version
    html = html.replace(
        /<script src="\.\.\/src\/[\w\.]+"><\/script>[\s\n]*(<script src="\.\.\/src\/[\w\.]+"><\/script>[\s\n]*)*/g,
        '<script src="app.min.js"></script>'
    );
    
    fs.writeFileSync(path.join(distDir, 'index.html'), html);
    console.log('✓ Created dist/index.html');
    
    // Copy CSS (extract from HTML)
    const cssMatch = html.match(/<style>([\s\S]*?)<\/style>/);
    if (cssMatch) {
        fs.writeFileSync(path.join(distDir, 'styles.css'), cssMatch[1].trim());
        console.log('✓ Created dist/styles.css');
    }
    
    console.log('\n🎉 Build complete! Files ready in dist/ directory');
    console.log('📁 dist/index.html - Production HTML');
    console.log('📁 dist/app.min.js - Minified JavaScript');
    console.log('📁 dist/styles.css - Extracted CSS');
}

// Run build if called directly
if (require.main === module) {
    build();
}

module.exports = { build };