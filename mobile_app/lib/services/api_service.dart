import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/alert_model.dart';
import '../utils/constants.dart';

/// HTTP client for the ATM surveillance REST API.
///
/// Extends [ChangeNotifier] so the UI can rebuild when alerts change.
class ApiService extends ChangeNotifier {
  ApiService() {
    _loadSettings();
  }

  String _baseUrl = AppConstants.defaultApiUrl;
  String _authToken = AppConstants.defaultAuthToken;
  List<AlertModel> _alerts = [];
  Map<String, dynamic> _stats = {};
  bool _loading = false;
  String? _error;

  // ---------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------

  String get baseUrl => _baseUrl;
  String get authToken => _authToken;
  List<AlertModel> get alerts => List.unmodifiable(_alerts);
  Map<String, dynamic> get stats => Map.unmodifiable(_stats);
  bool get loading => _loading;
  String? get error => _error;

  // ---------------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------------

  Future<void> updateSettings({
    required String baseUrl,
    required String authToken,
  }) async {
    _baseUrl = baseUrl;
    _authToken = authToken;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConstants.prefBaseUrl, baseUrl);
    await prefs.setString(AppConstants.prefAuthToken, authToken);
    notifyListeners();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString(AppConstants.prefBaseUrl) ?? AppConstants.defaultApiUrl;
    _authToken = prefs.getString(AppConstants.prefAuthToken) ?? AppConstants.defaultAuthToken;
    notifyListeners();
  }

  // ---------------------------------------------------------------------------
  // API calls
  // ---------------------------------------------------------------------------

  Map<String, String> get _headers => {
        'X-Auth-Token': _authToken,
        'Content-Type': 'application/json',
      };

  /// Fetch the list of alerts.
  Future<void> fetchAlerts({
    int limit = 50,
    int offset = 0,
    String? activityType,
    bool? acknowledged,
  }) async {
    _setLoading(true);
    try {
      final params = <String, String>{
        'limit': '$limit',
        'offset': '$offset',
        if (activityType != null) 'activity_type': activityType,
        if (acknowledged != null) 'acknowledged': '$acknowledged',
      };
      final uri = Uri.parse('$_baseUrl/alerts').replace(queryParameters: params);
      final response = await http.get(uri, headers: _headers).timeout(
            const Duration(seconds: AppConstants.requestTimeoutSeconds),
          );
      _handleResponse(response, (data) {
        final list = data['alerts'] as List<dynamic>? ?? [];
        _alerts = list
            .map((e) => AlertModel.fromJson(e as Map<String, dynamic>))
            .toList();
      });
    } catch (e) {
      _error = e.toString();
    } finally {
      _setLoading(false);
    }
  }

  /// Acknowledge an alert by ID.
  Future<bool> acknowledgeAlert(String alertId) async {
    try {
      final uri = Uri.parse('$_baseUrl/alerts/acknowledge');
      final response = await http
          .post(uri,
              headers: _headers, body: jsonEncode({'alert_id': alertId}))
          .timeout(const Duration(seconds: AppConstants.requestTimeoutSeconds));
      if (response.statusCode == 200) {
        final idx = _alerts.indexWhere((a) => a.id == alertId);
        if (idx != -1) {
          _alerts[idx] = _alerts[idx].copyWith(acknowledged: true);
          notifyListeners();
        }
        return true;
      }
    } catch (e) {
      _error = e.toString();
    }
    return false;
  }

  /// Fetch system statistics.
  Future<void> fetchStats() async {
    try {
      final uri = Uri.parse('$_baseUrl/stats');
      final response = await http.get(uri, headers: _headers).timeout(
            const Duration(seconds: AppConstants.requestTimeoutSeconds),
          );
      _handleResponse(response, (data) => _stats = data);
    } catch (e) {
      _error = e.toString();
    }
  }

  /// Build the full URL for an alert snapshot image.
  String imageUrl(String filename) =>
      '$_baseUrl/alerts/image/$filename';

  /// Check API health.
  Future<bool> checkHealth() async {
    try {
      final uri = Uri.parse('$_baseUrl/health');
      final response = await http
          .get(uri)
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  void _setLoading(bool value) {
    _loading = value;
    _error = null;
    notifyListeners();
  }

  void _handleResponse(
    http.Response response,
    void Function(Map<String, dynamic>) onSuccess,
  ) {
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      onSuccess(data);
      notifyListeners();
    } else {
      _error = 'Server error ${response.statusCode}';
    }
  }
}
