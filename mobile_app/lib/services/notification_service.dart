import 'dart:async';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../models/alert_model.dart';
import '../utils/constants.dart';

/// Manages push notifications from Firebase Cloud Messaging (FCM) and
/// displays them as local notifications when the app is in the foreground.
///
/// Background FCM messages are handled by the top-level
/// `_firebaseMessagingBackgroundHandler` function registered in `main.dart`.
class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  /// Callback invoked when a notification is tapped.  The payload contains
  /// the ``alert_id`` so the app can navigate to the detail screen.
  void Function(String alertId)? onNotificationTap;

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------

  Future<void> init() async {
    // Initialise local notifications plugin.
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _plugin.initialize(
      settings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
    );

    // Request FCM notification permissions.
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // Handle FCM messages received while the app is in the foreground.
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle notification tap when the app was in the background.
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);
  }

  // ---------------------------------------------------------------------------
  // FCM message handlers
  // ---------------------------------------------------------------------------

  void _handleForegroundMessage(RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;
    _showLocalNotification(
      title: notification.title ?? AppConstants.appName,
      body: notification.body ?? '',
      payload: message.data['alert_id'] ?? '',
    );
  }

  void _handleNotificationTap(RemoteMessage message) {
    final alertId = message.data['alert_id'];
    if (alertId != null && onNotificationTap != null) {
      onNotificationTap!(alertId as String);
    }
  }

  // ---------------------------------------------------------------------------
  // Local notification display
  // ---------------------------------------------------------------------------

  Future<void> showAlertNotification(AlertModel alert) async {
    await _showLocalNotification(
      title: '\u26a0 ${alert.activity}',
      body:
          '${alert.location} — ${(alert.confidence * 100).toStringAsFixed(0)}% confidence',
      payload: alert.id,
    );
  }

  Future<void> _showLocalNotification({
    required String title,
    required String body,
    String payload = '',
  }) async {
    const androidDetails = AndroidNotificationDetails(
      AppConstants.fcmChannelId,
      AppConstants.fcmChannelName,
      channelDescription: AppConstants.fcmChannelDescription,
      importance: Importance.max,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _plugin.show(
      payload.hashCode,
      title,
      body,
      details,
      payload: payload,
    );
  }

  void _onNotificationResponse(NotificationResponse response) {
    final alertId = response.payload;
    if (alertId != null && alertId.isNotEmpty && onNotificationTap != null) {
      onNotificationTap!(alertId);
    }
  }
}
