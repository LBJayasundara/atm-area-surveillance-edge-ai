import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:photo_view/photo_view.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../services/firebase_service.dart';
import '../widgets/activity_badge.dart';

/// Full alert detail view with zoomable snapshot image.
///
/// The snapshot is loaded from Firebase Storage when [AlertModel.imageUrl] is
/// set; otherwise it falls back to the legacy REST API image endpoint.
class AlertDetailScreen extends StatelessWidget {
  const AlertDetailScreen({super.key, required this.alert});

  final AlertModel alert;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiService>();

    // Prefer Firebase Storage URL; fall back to legacy REST API image path.
    final imageUrl = alert.imageUrl.isNotEmpty
        ? alert.imageUrl
        : (alert.image.isNotEmpty ? api.imageUrl(alert.image) : null);

    final formattedTime =
        DateFormat('MMM d, y • HH:mm:ss').format(alert.timestamp.toLocal());

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alert Details'),
        actions: [
          if (!alert.acknowledged)
            TextButton.icon(
              icon: const Icon(Icons.check),
              label: const Text('Acknowledge'),
              onPressed: () => _acknowledge(context),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Activity badge
          Center(child: ActivityBadge(activityType: alert.activityType)),
          const SizedBox(height: 8),
          Center(
            child: Text(
              alert.activity,
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 16),

          // Snapshot image
          if (imageUrl != null) _SnapshotImage(imageUrl: imageUrl),
          const SizedBox(height: 16),

          // Info table
          _InfoRow(label: 'Object', value: alert.detectedObject),
          _InfoRow(
            label: 'Confidence',
            value: '${(alert.confidence * 100).toStringAsFixed(1)}%',
          ),
          _InfoRow(label: 'Time', value: formattedTime),
          _InfoRow(label: 'Location', value: alert.location),
          _InfoRow(label: 'Zone', value: alert.metadata['zone'] ?? '—'),
          _InfoRow(label: 'Camera', value: alert.metadata['camera_id'] ?? '—'),
          _InfoRow(
            label: 'Status',
            value: alert.acknowledged ? 'Acknowledged' : 'Pending',
          ),
          if (alert.metadata['duration_seconds'] != null)
            _InfoRow(
              label: 'Duration',
              value: '${alert.metadata['duration_seconds']} s',
            ),
        ],
      ),
    );
  }

  Future<void> _acknowledge(BuildContext context) async {
    bool ok = false;

    // Try Firestore acknowledgement first.
    try {
      final fb = context.read<FirebaseService>();
      await fb.acknowledgeAlert(alert.id);
      ok = true;
    } catch (_) {
      // Fall back to REST API.
      ok = await context.read<ApiService>().acknowledgeAlert(alert.id);
    }

    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ok ? 'Alert acknowledged.' : 'Failed.')),
      );
      if (ok) Navigator.pop(context);
    }
  }
}

class _SnapshotImage extends StatelessWidget {
  const _SnapshotImage({required this.imageUrl});

  final String imageUrl;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => Scaffold(
            appBar: AppBar(title: const Text('Snapshot')),
            body: PhotoView(imageProvider: CachedNetworkImageProvider(imageUrl)),
          ),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: CachedNetworkImage(
          imageUrl: imageUrl,
          height: 220,
          width: double.infinity,
          fit: BoxFit.cover,
          placeholder: (_, __) => Container(
            height: 220,
            color: Colors.grey[200],
            child: const Center(child: CircularProgressIndicator()),
          ),
          errorWidget: (_, __, ___) => Container(
            height: 220,
            color: Colors.grey[200],
            child: const Icon(Icons.broken_image, size: 48),
          ),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
