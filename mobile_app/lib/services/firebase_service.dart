import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/alert_model.dart';
import '../utils/constants.dart';

/// Firestore data-access service.
///
/// Provides real-time [Stream]s and one-shot [Future]s for alert documents
/// stored in Firebase Firestore.  All reads are scoped to the
/// [AppConstants.firestoreAlertsCollection] collection.
class FirebaseService {
  FirebaseService() : _firestore = FirebaseFirestore.instance;

  // Visible for testing.
  FirebaseService.withFirestore(this._firestore);

  final FirebaseFirestore _firestore;

  // ---------------------------------------------------------------------------
  // Real-time streams
  // ---------------------------------------------------------------------------

  /// Continuous stream of the most recent [limit] alerts, newest first.
  Stream<List<AlertModel>> getAlertsStream({int limit = 50}) {
    return _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .orderBy('timestamp', descending: true)
        .limit(limit)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map(AlertModel.fromFirestore).toList());
  }

  /// Stream of alerts filtered by [activityType] (e.g. ``"weapon"``).
  Stream<List<AlertModel>> getAlertsByTypeStream(String activityType) {
    return _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .where('activity_type', isEqualTo: activityType)
        .orderBy('timestamp', descending: true)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map(AlertModel.fromFirestore).toList());
  }

  /// Stream of unacknowledged alerts only.
  Stream<List<AlertModel>> getUnacknowledgedAlertsStream() {
    return _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .where('acknowledged', isEqualTo: false)
        .orderBy('timestamp', descending: true)
        .snapshots()
        .map((snapshot) =>
            snapshot.docs.map(AlertModel.fromFirestore).toList());
  }

  // ---------------------------------------------------------------------------
  // One-shot reads
  // ---------------------------------------------------------------------------

  /// Fetch a single alert by its Firestore document ID.
  ///
  /// Returns ``null`` if the document does not exist.
  Future<AlertModel?> getAlert(String alertId) async {
    final doc = await _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .doc(alertId)
        .get();
    if (!doc.exists) return null;
    return AlertModel.fromFirestore(doc);
  }

  /// Fetch aggregate alert statistics for the last 24 hours.
  Future<Map<String, int>> getAlertStats() async {
    final since = Timestamp.fromDate(
      DateTime.now().subtract(const Duration(days: 1)),
    );
    final snapshot = await _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .where('timestamp', isGreaterThan: since)
        .get();

    final stats = <String, int>{
      'total': snapshot.docs.length,
      'weapon': 0,
      'loitering': 0,
      'concealment': 0,
    };

    for (final doc in snapshot.docs) {
      final type = doc.get('activity_type') as String? ?? '';
      stats[type] = (stats[type] ?? 0) + 1;
    }

    return stats;
  }

  // ---------------------------------------------------------------------------
  // Writes
  // ---------------------------------------------------------------------------

  /// Mark an alert as acknowledged.
  Future<void> acknowledgeAlert(String alertId) {
    return _firestore
        .collection(AppConstants.firestoreAlertsCollection)
        .doc(alertId)
        .update({
      'acknowledged': true,
      'acknowledged_at': FieldValue.serverTimestamp(),
    });
  }
}
