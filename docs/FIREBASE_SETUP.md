# Firebase Setup Guide

This guide explains how to create and configure a Firebase project for the
ATM Area Surveillance system.

## Prerequisites

- Google account
- Firebase CLI (`npm install -g firebase-tools`)
- Flutter SDK

---

## 1. Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com).
2. Click **Add project** and enter a project name (e.g. `atm-surveillance`).
3. Disable Google Analytics (optional) and click **Create project**.

---

## 2. Enable Required Firebase Services

### Cloud Firestore

1. In the Firebase Console, select your project.
2. Navigate to **Build → Firestore Database**.
3. Click **Create database**.
4. Choose **Start in production mode** and select your nearest region.
5. Click **Enable**.

### Firebase Storage

1. Navigate to **Build → Storage**.
2. Click **Get started**.
3. Accept the default security rules (you will replace them later).
4. Select the same region as Firestore.

### Firebase Cloud Messaging (FCM)

FCM is enabled automatically for every Firebase project.  No manual setup is
required.

### Firebase Authentication (Optional)

If you want to restrict access to authenticated users:

1. Navigate to **Build → Authentication**.
2. Click **Get started**.
3. Enable **Email/Password** (or any provider you prefer).

---

## 3. Configure the Raspberry Pi (Python) Backend

### Download the Service Account Key

1. In the Firebase Console, go to **Project Settings → Service accounts**.
2. Click **Generate new private key**.
3. Save the downloaded JSON file to:

   ```
   config/firebase-credentials.json
   ```

   > ⚠ **Never commit this file to version control.**  It is listed in
   > `.gitignore`.

### Update `config/config.yaml`

Edit the `firebase` section to match your project:

```yaml
firebase:
  credentials_path: "config/firebase-credentials.json"
  storage_bucket: "your-project-id.appspot.com"   # replace with real project ID
  collection_name: "alerts"
  fcm_topic: "atm_alerts"
```

---

## 4. Configure the Flutter Mobile App

### Android

1. In the Firebase Console, click the **Android** icon to add an Android app.
2. Enter the package name from `mobile_app/android/app/build.gradle`
   (`applicationId`).
3. Download `google-services.json` and place it at:

   ```
   mobile_app/android/app/google-services.json
   ```

   > ⚠ **Never commit this file to version control.**  It is listed in
   > `.gitignore`.

4. The `mobile_app/android/app/google-services.template.json` file shows the
   expected structure.

### iOS

1. Click the **iOS** icon to add an iOS app.
2. Enter the Bundle ID from `mobile_app/ios/Runner.xcodeproj`.
3. Download `GoogleService-Info.plist` and place it at:

   ```
   mobile_app/ios/Runner/GoogleService-Info.plist
   ```

   > ⚠ **Never commit this file to version control.**  It is listed in
   > `.gitignore`.

4. See `mobile_app/ios/Runner/GoogleService-Info.template.plist` for the
   expected structure.

---

## 5. Deploy Firestore Security Rules

```bash
firebase login
firebase use --add       # select your project
firebase deploy --only firestore:rules
```

The rules file is `firestore.rules` in the repository root.

---

## 6. Deploy Storage Security Rules

```bash
firebase deploy --only storage:rules
```

The rules file is `storage.rules` in the repository root.

---

## 7. Deploy Cloud Functions (Optional)

The Cloud Function in `functions/index.js` sends FCM notifications
automatically when a new alert document is written to Firestore.

```bash
cd functions
npm install
firebase deploy --only functions
```

> **Note:** Cloud Functions require the **Blaze (pay-as-you-go)** billing plan.

---

## 8. Firestore Database Structure

```
/alerts (collection)
  /{alertId} (document)
    - alert_id: string
    - activity: string          e.g. "Weapon Detected"
    - activity_type: string     "weapon" | "loitering" | "concealment"
    - detected_object: string   "gun" | "knife" | "helmet" | "mask"
    - confidence: number        0.0 – 1.0
    - timestamp: timestamp
    - location: string          e.g. "ATM Entrance"
    - image_url: string         Firebase Storage public URL
    - acknowledged: boolean
    - acknowledged_at: timestamp  (set when acknowledged)
    - metadata: map
        - person_id: number
        - bounding_box: array [x1, y1, x2, y2]
        - zone: string
        - camera_id: string

/system_stats (collection)
  /daily (document)
    - date: string
    - total_alerts: number
    - weapon_count: number
    - loitering_count: number
    - concealment_count: number
    - last_updated: timestamp
```

---

## 9. FCM Topics

The system uses a single topic for all alert notifications:

| Topic | Description |
|-------|-------------|
| `atm_alerts` | All suspicious activity alerts |

The Flutter app subscribes to this topic on startup (`main.dart`).

---

## 10. Testing Firebase Integration

### Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run Firebase tests (mock-based, no real credentials needed)
python -m pytest tests/test_firebase.py -v
```

### End-to-end test

1. Start the Raspberry Pi surveillance system:
   ```bash
   python main.py --config config/config.yaml
   ```
2. A test alert should appear in the Firestore console under
   **Firestore Database → alerts**.
3. The Flutter app should receive a push notification within a few seconds.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `FileNotFoundError: config/firebase-credentials.json` | Download and place the service account key file |
| `Permission denied` when writing to Firestore | Ensure the service account has the **Firebase Admin SDK Administrator Service Agent** role |
| FCM notifications not received | Verify the app is subscribed to the `atm_alerts` topic; check FCM quota |
| Storage upload fails | Ensure the service account has **Storage Admin** or **Storage Object Creator** role |
| Images not visible in app | Make sure `blob.make_public()` is called after upload, or set Storage rules to allow authenticated reads |
