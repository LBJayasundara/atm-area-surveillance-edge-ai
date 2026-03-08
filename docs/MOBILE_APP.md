# Flutter Mobile App Guide

## Prerequisites

- Flutter SDK 3.x: https://flutter.dev/docs/get-started/install
- Android Studio or Xcode

## Build for Android

```bash
cd mobile_app
flutter pub get
flutter build apk --release
# APK: build/app/outputs/flutter-apk/app-release.apk
```

## Build for iOS

```bash
cd mobile_app
flutter pub get
flutter build ios --release
```

## Configuration

1. Open the app and navigate to **Settings**.
2. Set **API Base URL** to `http://<raspberry-pi-ip>:5000`.
3. Set **Auth Token** to match `api.auth_token` in `config/config.yaml`.
4. Tap **Save Settings**.

## Features

| Screen | Description |
|--------|-------------|
| Dashboard | System status, alert statistics |
| Alerts | Scrollable alert list with filters |
| Alert Detail | Full details with zoomable snapshot image |
| Settings | API URL and auth token configuration |

## Notification Setup

The app polls the API every 15 seconds for new alerts and shows local
push notifications. No FCM/APNs setup required.

## Permissions Required

- **Internet** — API communication
- **Notifications** — Alert push notifications
