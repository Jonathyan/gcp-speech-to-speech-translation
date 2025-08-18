# Firebase Hosting Manual Setup Guide

## Current Status
✅ Firebase project added to GCP project `lfhs-translate`  
✅ Firebase and Firebase Hosting APIs enabled  
✅ Frontend built and configured for production  
⏳ Firebase Hosting site needs to be created  

## Required Manual Steps

Since the Firebase CLI requires interactive input, please complete these steps manually:

### Step 1: Enable Firebase Hosting in Console

1. **Go to Firebase Console**: https://console.firebase.google.com/project/lfhs-translate
2. **Navigate to Hosting**: Click "Hosting" in the left sidebar
3. **Get Started**: Click "Get started" button
4. **Complete setup**: Follow the setup wizard to enable hosting

### Step 2: Alternative - Use Firebase CLI Interactively

If you prefer using the CLI, run these commands **interactively** (not in this session):

```bash
cd frontend
firebase init hosting
# Select:
# - Use existing project: lfhs-translate
# - Public directory: dist
# - Single-page app: Yes
# - Overwrite index.html: No
```

### Step 3: Deploy After Setup

Once hosting is enabled, run:

```bash
./deploy-firebase.sh
```

## Alternative Deployment Options

If Firebase continues to have issues, you can use these alternatives:

### Option 1: Vercel (Recommended Alternative)
```bash
npx vercel --prod dist/
```

### Option 2: Netlify
1. Go to https://netlify.com
2. Drag and drop the `dist/` folder
3. Site will be live immediately

### Option 3: Cloud Storage Static Hosting
```bash
# Create bucket
gsutil mb gs://lfhs-translate-frontend

# Enable static website hosting
gsutil web set -m index.html -e index.html gs://lfhs-translate-frontend

# Upload files
gsutil -m cp -r dist/* gs://lfhs-translate-frontend/

# Make public
gsutil -m acl ch -r -u AllUsers:R gs://lfhs-translate-frontend/*
```

## Expected Result After Deployment

**Frontend URL**: `https://lfhs-translate.firebaseapp.com` (or alternative hosting URL)  
**Backend URL**: `https://hybrid-stt-service-ysw2dobxea-ew.a.run.app` ✅ (already live)

## Testing the Complete System

1. **Open frontend URL** in two browser tabs/windows
2. **Tab 1 - Speaker**:
   - Enter stream ID: `test-room-123`
   - Click "Start Uitzending"
   - Grant microphone permission
   - Speak in Dutch
3. **Tab 2 - Listener**:
   - Enter same stream ID: `test-room-123`  
   - Click "Luisten"
   - Should hear English translation in real-time

## Files Ready for Deployment

✅ `dist/index.html` - Production HTML (2.2KB)  
✅ `dist/app.min.js` - Production JavaScript (109.9KB)  
✅ `dist/styles.css` - Production CSS (1.0KB)  
✅ `firebase.json` - Firebase hosting configuration  
✅ `.firebaserc` - Firebase project configuration  

## Support

The technical setup is complete. The only remaining step is enabling Firebase Hosting through the console or interactive CLI, then running the deployment script.