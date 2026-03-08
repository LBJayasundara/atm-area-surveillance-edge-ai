import 'dart:async';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../models/alert_model.dart';
import '../utils/constants.dart';

/// Manages local push notifications and background polling.
class NotificationService {
  NotificationService._();

  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();

  Timer? _pollingTimer;

  // ---------------------------------------------------------------------------
  // Initialisation
  // ---------------------------------------------------------------------------

  Future<void> init() async {
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
    await _plugin.initialize(settings);
  }

  // ---------------------------------------------------------------------------
  // Show notification
  // ---------------------------------------------------------------------------

  Future<void> showAlertNotification(AlertModel alert) async {
    const androidDetails = AndroidNotificationDetails(
      'atm_alerts',
      'ATM Alerts',
      channelDescription: 'Suspicious activity notifications',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _plugin.show(
      alert.id.hashCode,
      '⚠ ${alert.activity}',
      '${alert.location} — ${(alert.confidence * 100).toStringAsFixed(0)}% confidence',
      details,
    );
  }

  // ---------------------------------------------------------------------------
  // Polling
  // ---------------------------------------------------------------------------

  /// Start polling the API for new alerts every [intervalSeconds] seconds.
  void startPolling({
    required Future<List<AlertModel>> Function() fetchLatest,
    int intervalSeconds = AppConstants.pollingIntervalSeconds,
  }) {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(
      Duration(seconds: intervalSeconds),
      (_) async {
        try {
          final newAlerts = await fetchLatest();
          for (final alert in newAlerts) {
            await showAlertNotification(alert);
          }
        } catch (_) {
          // Ignore polling errors silently
        }
      },
    );
  }

  void stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }
}
