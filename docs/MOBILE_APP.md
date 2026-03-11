# Mobile App — Detailed Design & Implementation Guide

The ATM Surveillance mobile app is a **Flutter 3** cross-platform application
(Android + iOS) that gives security personnel real-time access to the ATM area
surveillance system.  It connects either directly to the Raspberry Pi REST API
over the local network or to **Firebase** (Firestore + Cloud Storage + FCM) for
cloud-based access from anywhere.

---

## Table of Contents

1. [Concept & Purpose](#1-concept--purpose)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Screens & User Flows](#3-screens--user-flows)
   - [Dashboard (Home)](#31-dashboard-home)
   - [Alerts List](#32-alerts-list)
   - [Alert Detail](#33-alert-detail)
   - [Settings](#34-settings)
4. [Data Model](#4-data-model)
5. [Services Layer](#5-services-layer)
   - [ApiService — REST API client](#51-apiservice--rest-api-client)
   - [FirebaseService — Firestore client](#52-firebaseservice--firestore-client)
   - [NotificationService — Push notifications](#53-notificationservice--push-notifications)
6. [State Management](#6-state-management)
7. [UI Components](#7-ui-components)
8. [Notification System](#8-notification-system)
9. [Dual Backend Strategy](#9-dual-backend-strategy)
10. [Security](#10-security)
11. [Dependencies](#11-dependencies)
12. [Build & Configuration Guide](#12-build--configuration-guide)
13. [Permissions Required](#13-permissions-required)

---

## 1. Concept & Purpose

Security personnel patrolling an ATM site cannot watch live camera feeds
continuously.  The mobile app solves this by:

- Surfacing **instant push notifications** whenever the edge AI detects a
  suspicious event (weapon drawn, face concealment, or loitering).
- Providing a **real-time alert feed** that updates the moment a new event is
  written to the backend.
- Allowing operators to **review snapshot images** captured at the moment of
  detection and **acknowledge** alerts to track response.
- Showing a **dashboard** with system health and alert statistics so dispatchers
  can gauge overall activity at a glance.

The app is intentionally lightweight: no live video streaming is involved.
All video processing happens on the Raspberry Pi; only text metadata and
small JPEG snapshots travel to the app.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Flutter Mobile App                      │
│                                                           │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ HomeScreen  │  │AlertListScreen│  │SettingsScreen  │  │
│  │ (Dashboard) │  │               │  │                │  │
│  └──────┬──────┘  └───────┬───────┘  └───────┬────────┘  │
│         │                 │                   │           │
│  ┌──────▼─────────────────▼───────────────────▼────────┐  │
│  │            State Management (Provider)               │  │
│  │   ApiService (ChangeNotifier)   FirebaseService      │  │
│  └──────┬─────────────────────────────────┬────────────┘  │
│         │                                 │               │
│  ┌──────▼──────┐                 ┌────────▼───────────┐   │
│  │ REST API    │                 │   Firebase Suite   │   │
│  │ (Flask /    │                 │ Firestore (alerts) │   │
│  │  RPi 4)     │                 │ Storage (images)   │   │
│  └─────────────┘                 │ FCM (push notifs)  │   │
│                                  └────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          NotificationService (FCM + local)           │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Data flow for a new alert:**

```
RPi detects event
      │
      ├─► SQLite (local)  ──► Flask REST API  ──► ApiService (polling fallback)
      │
      └─► Firebase Client ──► Firestore       ──► FirebaseService (real-time stream)
                          └─► Firebase Storage (JPEG snapshot)
                          └─► Cloud Functions ──► FCM ──► NotificationService
```

---

## 3. Screens & User Flows

The app uses a **bottom navigation bar** with three tabs:

| Tab | Icon | Screen |
|-----|------|--------|
| 0 | Dashboard | `HomeScreen` |
| 1 | Alerts | `AlertListScreen` |
| 2 | Settings | `SettingsScreen` |

Navigation between tabs is instantaneous (no page transitions) because all
three screens are kept alive in a `List<Widget>`.

---

### 3.1 Dashboard (Home)

**File:** `lib/screens/home_screen.dart`

**Purpose:** At-a-glance operational overview for dispatchers.

**Layout:**

```
┌─────────────────────────────────┐
│  ATM Surveillance        ⟳      │  ← AppBar with refresh button
├─────────────────────────────────┤
│  ┌───────────────────────────┐  │
│  │  🟢 System Online         │  │  ← StatusCard: green/red videocam icon
│  │  Surveillance active      │  │
│  └───────────────────────────┘  │
│                                 │
│  Statistics (last 24 h)         │
│  ┌──────────┐  ┌─────────────┐  │
│  │    12    │  │    🔴  3    │  │  ← Total Alerts / Weapons (red if > 0)
│  │  Total   │  │   Weapons   │  │
│  └──────────┘  └─────────────┘  │
│  ┌──────────┐  ┌─────────────┐  │
│  │  🟠  5   │  │  🟠  4      │  │  ← Loitering / Concealment (orange if > 0)
│  │ Loitering│  │ Concealment │  │
│  └──────────┘  └─────────────┘  │
└─────────────────────────────────┘
```

**Behaviour:**

- On mount, calls `ApiService.checkHealth()` to determine if the Raspberry Pi
  is reachable, then renders a green (`System Online`) or red (`System Offline`)
  status card.
- Concurrently queries Firestore via `FirebaseService.getAlertStats()` for last-
  24-hour breakdown.  If Firestore is unavailable, falls back to
  `ApiService.fetchStats()` which reads from the SQLite-backed REST API.
- Pull-to-refresh and the AppBar refresh button both re-run the same logic.
- Stats tiles turn **red** (weapons) or **orange** (loitering / concealment)
  when non-zero to draw attention to active threats.

---

### 3.2 Alerts List

**File:** `lib/screens/alert_list_screen.dart`

**Purpose:** Live, filterable feed of all surveillance alerts.

**Layout:**

```
┌─────────────────────────────────────┐
│  Alerts                             │  ← AppBar
├─────────────────────────────────────┤
│  [Unacknowledged] [weapon] [conc..] │  ← Horizontal FilterChip bar
│                   [loitering]       │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │
│  │ 🔴 WEAPON   Knife Detected  NEW │    ← AlertCard (unread badge)
│  │  ATM Zone A · knife             │
│  │  ⏱ 2 min ago             87%   │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │ 🟠 LOITER  Person Loitering     │
│  │  ATM Zone B · person            │
│  │  ⏱ 5 min ago             92%   │
│  └─────────────────────────────┘    │
│          ... more alerts ...        │
└─────────────────────────────────────┘
```

**Filter chips:**

| Chip | Effect |
|------|--------|
| **Unacknowledged** | Shows only alerts not yet actioned |
| **weapon** | Shows weapon-type alerts only |
| **concealment** | Shows face-concealment alerts only |
| **loitering** | Shows loitering alerts only |

Chips are mutually exclusive in the type dimension; the acknowledged filter
stacks independently.

**Data source:**

- Primary: **Firestore real-time stream** via `FirebaseService`.  The list
  updates *instantly* when a new alert document is written — no polling needed.
- Fallback: If Firestore throws (e.g. no Firebase config), a legacy
  `_LegacyAlertList` widget takes over and calls `ApiService.fetchAlerts()`.

Tapping any `AlertCard` pushes `AlertDetailScreen` onto the navigation stack.

---

### 3.3 Alert Detail

**File:** `lib/screens/alert_detail_screen.dart`

**Purpose:** Full information for a single alert, with snapshot image.

**Layout:**

```
┌─────────────────────────────────────┐
│  Alert Details         [✓ Acknowledge]│  ← Only shown if not yet acknowledged
├─────────────────────────────────────┤
│            🔴 WEAPON                │  ← ActivityBadge (large)
│         Knife Detected              │
│                                     │
│  ┌─────────────────────────────┐    │
│  │       [snapshot image]      │    │  ← Tap to open full-screen zoomable view
│  └─────────────────────────────┘    │
│                                     │
│  Object      knife                  │
│  Confidence  87.4%                  │
│  Time        Mar 11, 2026 • 09:14   │
│  Location    ATM Zone A             │
│  Zone        zone_1                 │
│  Camera      cam_01                 │
│  Status      Pending                │
│  Duration    —                      │
└─────────────────────────────────────┘
```

**Image viewer:**

The snapshot is displayed using `CachedNetworkImage` at 220 px height.
Tapping it opens a full-screen `PhotoView` (pinch-to-zoom, pan) so operators
can examine fine details such as weapon type or face covering.

Images are loaded from Firebase Storage (`imageUrl` field) when available,
otherwise from the Raspberry Pi REST API endpoint (`GET /alerts/image/<file>`).

**Acknowledge flow:**

1. User taps **Acknowledge**.
2. App tries `FirebaseService.acknowledgeAlert(id)` first (sets
   `acknowledged: true` and `acknowledged_at` server timestamp in Firestore).
3. Falls back to `ApiService.acknowledgeAlert(id)` (`POST /alerts/acknowledge`)
   if Firestore is unavailable.
4. On success: shows a SnackBar and pops back to the Alerts list.
5. On failure: shows an error SnackBar and remains on the detail screen.

---

### 3.4 Settings

**File:** `lib/screens/settings_screen.dart`

**Purpose:** Configure how the app connects to the Raspberry Pi backend.

**Fields:**

| Field | Default | Stored in |
|-------|---------|-----------|
| API Base URL | `http://192.168.1.100:5000` | `SharedPreferences` |
| Auth Token | `change-me-in-production` | `SharedPreferences` |

Settings are saved to device storage via `SharedPreferences` and loaded
automatically on startup through `ApiService._loadSettings()`.  Changes take
effect immediately because `ApiService` is a `ChangeNotifier` and calls
`notifyListeners()` after every save.

---

## 4. Data Model

**File:** `lib/models/alert_model.dart`

`AlertModel` is an **immutable** value class that represents one surveillance
alert.  It supports two factory constructors to handle both data sources:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `String` | Unique alert ID (SQLite UUID or Firestore document ID) |
| `activity` | `String` | Human-readable description, e.g. `"Knife Detected"` |
| `activityType` | `String` | Machine tag: `weapon` / `concealment` / `loitering` |
| `detectedObject` | `String` | Specific object class, e.g. `"knife"`, `"person"` |
| `confidence` | `double` | YOLOv8 detection confidence 0.0–1.0 |
| `timestamp` | `DateTime` | UTC moment of detection |
| `location` | `String` | Zone label from zones.json, e.g. `"ATM Zone A"` |
| `image` | `String` | Local filename for REST API image endpoint |
| `imageUrl` | `String` | Firebase Storage HTTPS URL |
| `acknowledged` | `bool` | Whether an operator has reviewed the alert |
| `metadata` | `Map<String, dynamic>` | Extra fields: `zone`, `camera_id`, `duration_seconds` |

**Factory constructors:**

```
AlertModel.fromJson(Map<String, dynamic>)   // REST API JSON
AlertModel.fromFirestore(DocumentSnapshot)  // Firestore document
```

**`copyWith`** enables immutable updates (used when acknowledging an alert
locally before the server responds).

---

## 5. Services Layer

### 5.1 ApiService — REST API client

**File:** `lib/services/api_service.dart`  
**Base class:** `ChangeNotifier` (Provider)

Manages all HTTP communication with the Flask API running on the Raspberry Pi.

| Method | HTTP | Endpoint | Description |
|--------|------|----------|-------------|
| `fetchAlerts(...)` | GET | `/alerts` | Load alert list with optional filters |
| `acknowledgeAlert(id)` | POST | `/alerts/acknowledge` | Mark alert reviewed |
| `fetchStats()` | GET | `/stats` | Aggregate alert counts |
| `checkHealth()` | GET | `/health` | Ping for system-online status |
| `imageUrl(filename)` | — | `/alerts/image/<file>` | Build snapshot URL |

All requests attach the `X-Auth-Token` header for authentication.  A 10-second
timeout prevents the UI from hanging when the Pi is unreachable.

State fields exposed to the UI:

| Field | Type | Description |
|-------|------|-------------|
| `alerts` | `List<AlertModel>` | Last fetched alert list |
| `stats` | `Map<String, dynamic>` | Last fetched statistics |
| `loading` | `bool` | True while a request is in-flight |
| `error` | `String?` | Last error message, `null` on success |

---

### 5.2 FirebaseService — Firestore client

**File:** `lib/services/firebase_service.dart`

Provides real-time Firestore streams and one-shot reads/writes.

| Method | Returns | Description |
|--------|---------|-------------|
| `getAlertsStream({limit})` | `Stream<List<AlertModel>>` | Live stream newest-first |
| `getAlertsByTypeStream(type)` | `Stream<List<AlertModel>>` | Filtered by activity type |
| `getUnacknowledgedAlertsStream()` | `Stream<List<AlertModel>>` | Unreviewed only |
| `getAlert(id)` | `Future<AlertModel?>` | Single document look-up |
| `getAlertStats()` | `Future<Map<String, int>>` | Last-24h counts by type |
| `acknowledgeAlert(id)` | `Future<void>` | Set `acknowledged: true` in Firestore |

All alert documents live in the `alerts` Firestore collection (configurable
via `AppConstants.firestoreAlertsCollection`).

---

### 5.3 NotificationService — Push notifications

**File:** `lib/services/notification_service.dart`  
**Pattern:** Singleton (`NotificationService.instance`)

Bridges Firebase Cloud Messaging (FCM) with the device's local notification
system:

| Scenario | Handler |
|----------|---------|
| App **foreground**, FCM message arrives | `_handleForegroundMessage` → `_showLocalNotification` |
| App **background**, notification tapped | `_handleNotificationTap` → `onNotificationTap` callback |
| App **terminated**, FCM arrives | Top-level `_firebaseMessagingBackgroundHandler` in `main.dart` |
| Manual trigger (e.g., from polling fallback) | `showAlertNotification(alert)` |

Notification content format:

```
Title:  ⚠ Knife Detected
Body:   ATM Zone A — 87% confidence
```

The `payload` field carries the `alert_id` so a notification tap can navigate
directly to `AlertDetailScreen`.

---

## 6. State Management

The app uses the **Provider** package.  Two providers are registered at the
root `MaterialApp`:

```dart
MultiProvider(
  providers: [
    ChangeNotifierProvider(create: (_) => ApiService()),   // mutable, reactive
    Provider(create: (_) => FirebaseService()),             // immutable wrapper
  ],
  ...
)
```

`ApiService` is a `ChangeNotifier`; widgets call `context.watch<ApiService>()`
to rebuild when alerts or loading state changes.

`FirebaseService` exposes Dart `Stream`s consumed by `StreamBuilder` widgets
directly; no explicit `notifyListeners()` is needed.

---

## 7. UI Components

### AlertCard (`lib/widgets/alert_card.dart`)

Reusable list-item widget.  Renders:

- `ActivityBadge` (compact icon, 44×44) on the left.
- Alert title, location, and object in the centre column.
- Relative timestamp (`timeago` package) and confidence percentage.
- Red **NEW** badge when `alert.acknowledged == false`.
- Chevron icon on the right.

### ActivityBadge (`lib/widgets/activity_badge.dart`)

Colour-coded badge rendered in two sizes:

| `activityType` | Icon | Colour |
|----------------|------|--------|
| `weapon` | `Icons.gavel` | Red `#D32F2F` |
| `concealment` | `Icons.face_retouching_off` | Deep orange `#E65100` |
| `loitering` | `Icons.directions_walk` | Blue `#1565C0` |
| *(unknown)* | `Icons.warning_amber` | Grey |

- **Compact** (`compact: true`): 44×44 square icon only — used in `AlertCard`.
- **Full**: Icon + uppercase text label with border — used in `AlertDetailScreen`.

---

## 8. Notification System

Two delivery mechanisms work together:

### FCM (Firebase Cloud Messaging) — primary

1. The app subscribes to the `atm_alerts` FCM topic on startup.
2. When the Raspberry Pi writes a new alert to Firestore, a **Firebase Cloud
   Function** (`functions/index.js`) triggers and sends an FCM message to the
   `atm_alerts` topic.
3. `NotificationService` receives the message and shows a local notification
   regardless of whether the app is in the foreground, background, or
   terminated.

### REST API polling — fallback

If Firebase is not configured, `ApiService` polls `GET /alerts` every
15 seconds (`AppConstants.pollingIntervalSeconds`).  When a new alert is
detected (ID not seen before), `NotificationService.showAlertNotification()`
is called to display a local notification.

---

## 9. Dual Backend Strategy

The app is designed to work with **either** backend:

| Feature | Firebase backend | REST API backend |
|---------|-----------------|-----------------|
| Alert list | Firestore real-time stream | Poll every 15 s |
| Alert images | Firebase Storage HTTPS URL | `GET /alerts/image/<file>` |
| Statistics | Firestore query (24 h window) | `GET /stats` |
| Acknowledge | `FirebaseService.acknowledgeAlert` | `POST /alerts/acknowledge` |
| Push notifications | FCM via Cloud Functions | Local poll-based |

The app always **tries Firebase first** and silently falls back to the REST
API if Firestore throws an error (e.g. missing `google-services.json`).  This
means the app works on a local network without any internet connectivity as
long as it can reach the Raspberry Pi.

---

## 10. Security

| Concern | Mitigation |
|---------|-----------|
| API authentication | Every REST request sends `X-Auth-Token` header; token is stored in `SharedPreferences` (not in source code) |
| Default credentials | Default token is `change-me-in-production` — must be changed before deployment |
| Firestore access | Controlled by `firestore.rules`; write access is restricted to the server service account |
| Firebase Storage | Controlled by `storage.rules`; images are read-only for authenticated clients |
| Network transport | HTTPS for Firebase; for the local REST API, use nginx with TLS (see `deployment/nginx.conf`) |
| No PII stored | Alerts contain zone/location labels and confidence scores; no facial recognition or identity data |

---

## 11. Dependencies

Listed in `mobile_app/pubspec.yaml`:

| Package | Version | Purpose |
|---------|---------|---------|
| `firebase_core` | ^2.24.2 | Firebase SDK initialisation |
| `cloud_firestore` | ^4.13.6 | Real-time alert database |
| `firebase_storage` | ^11.5.6 | Snapshot image URLs |
| `firebase_messaging` | ^14.7.9 | FCM push notifications |
| `firebase_auth` | ^4.15.3 | Firebase authentication support |
| `provider` | ^6.1.1 | State management |
| `http` | ^1.1.0 | REST API HTTP client |
| `flutter_local_notifications` | ^16.1.0 | Local notification display |
| `cached_network_image` | ^3.3.0 | Image caching and loading |
| `intl` | ^0.18.1 | Date/time formatting |
| `shared_preferences` | ^2.2.2 | Persistent settings storage |
| `photo_view` | ^0.14.0 | Pinch-to-zoom snapshot viewer |
| `timeago` | ^3.5.0 | Relative time strings ("2 min ago") |

---

## 12. Build & Configuration Guide

### Prerequisites

- Flutter SDK 3.x — https://flutter.dev/docs/get-started/install
- Android Studio (Android) or Xcode 14+ (iOS)

### Step 1 — Install dependencies

```bash
cd mobile_app
flutter pub get
```

### Step 2 — Firebase setup (optional but recommended)

If you want real-time streaming and FCM push notifications:

1. Create a Firebase project (see [FIREBASE_SETUP.md](FIREBASE_SETUP.md)).
2. Place `google-services.json` in `mobile_app/android/app/`.
3. Place `GoogleService-Info.plist` in `mobile_app/ios/Runner/`.

If you skip this step the app falls back to REST API polling automatically.

### Step 3 — Run in development

```bash
flutter run          # connects to a device/emulator
```

### Step 4 — Build for release

**Android:**
```bash
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

**iOS:**
```bash
flutter build ios --release
# Then archive in Xcode for distribution
```

### Step 5 — Configure the app at runtime

1. Open the app and navigate to the **Settings** tab (⚙).
2. Set **API Base URL** to `http://<raspberry-pi-ip>:5000`.
3. Set **Auth Token** to the value of `api.auth_token` in `config/config.yaml`.
4. Tap **Save Settings**.

Settings are persisted automatically and survive app restarts.

---

## 13. Permissions Required

| Permission | Platform | Reason |
|-----------|----------|--------|
| `INTERNET` | Android | REST API and Firebase network calls |
| `POST_NOTIFICATIONS` | Android 13+ | Show local alert notifications |
| `NSAppTransportSecurity` | iOS | Allow plain HTTP to local Raspberry Pi |
| Notification permission | iOS | Show local alert notifications (requested at runtime) |
