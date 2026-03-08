/**
 * Firebase Cloud Function — ATM Surveillance Alert Notifications
 *
 * Triggered when a new document is created in the /alerts collection.
 * Sends an FCM push notification to the "atm_alerts" topic so all
 * subscribed Flutter clients receive an immediate alert.
 *
 * Deploy with:
 *   cd functions && npm install && firebase deploy --only functions
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');

// Initialise Admin SDK (uses the Cloud Functions service account automatically).
admin.initializeApp();

/**
 * onAlertCreated — fires whenever a new alert document is added to Firestore.
 */
exports.onAlertCreated = functions.firestore
  .document('alerts/{alertId}')
  .onCreate(async (snap, context) => {
    const alert = snap.data();
    const alertId = context.params.alertId;

    const confidencePct = alert.confidence
      ? `${(alert.confidence * 100).toFixed(0)}%`
      : 'N/A';

    const message = {
      notification: {
        title: `\u{1F6A8} ${alert.activity || 'Suspicious Activity'}`,
        body: `Confidence: ${confidencePct} | ${alert.location || ''}`,
      },
      data: {
        alert_id: alertId,
        activity_type: alert.activity_type || '',
        click_action: 'FLUTTER_NOTIFICATION_CLICK',
      },
      topic: 'atm_alerts',
    };

    try {
      const response = await admin.messaging().send(message);
      console.log(`Notification sent for alert ${alertId}:`, response);
    } catch (error) {
      console.error(`Failed to send notification for alert ${alertId}:`, error);
    }
  });

/**
 * onAlertAcknowledged — updates daily statistics when an alert is acknowledged.
 */
exports.onAlertAcknowledged = functions.firestore
  .document('alerts/{alertId}')
  .onUpdate(async (change, context) => {
    const before = change.before.data();
    const after = change.after.data();

    // Only act when the acknowledged flag transitions false → true.
    if (!before.acknowledged && after.acknowledged) {
      console.log(`Alert ${context.params.alertId} acknowledged.`);
    }
  });
