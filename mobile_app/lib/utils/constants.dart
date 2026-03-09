import 'package:flutter/material.dart';

/// App-wide constants.
abstract class AppConstants {
  static const String appName = 'ATM Surveillance';
  static const String appVersion = '1.0.0';
  static const Color primaryColor = Color(0xFF1565C0);

  // Shared preferences keys
  static const String prefBaseUrl = 'api_base_url';
  static const String prefAuthToken = 'api_auth_token';

  // Defaults
  static const String defaultApiUrl = 'http://192.168.1.100:5000';
  static const String defaultAuthToken = 'change-me-in-production';

  // HTTP
  static const int requestTimeoutSeconds = 10;
  static const int pollingIntervalSeconds = 15;

  // Firebase / Firestore
  static const String firestoreAlertsCollection = 'alerts';

  // Firebase Cloud Messaging
  static const String fcmAlertsTopic = 'atm_alerts';
  static const String fcmChannelId = 'atm_alerts';
  static const String fcmChannelName = 'ATM Alerts';
  static const String fcmChannelDescription =
      'Suspicious activity alerts from ATM surveillance';
}
