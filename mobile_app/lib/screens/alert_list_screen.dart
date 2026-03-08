import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../services/firebase_service.dart';
import '../widgets/alert_card.dart';
import 'alert_detail_screen.dart';

/// Scrollable list of alerts with filter chips.
///
/// Displays alerts from Firestore using a real-time [StreamBuilder] so the
/// list updates instantly when new alerts arrive.  Falls back to polling the
/// REST API if Firestore is unavailable.
class AlertListScreen extends StatefulWidget {
  const AlertListScreen({super.key});

  @override
  State<AlertListScreen> createState() => _AlertListScreenState();
}

class _AlertListScreenState extends State<AlertListScreen> {
  String? _filterType;
  bool? _filterAcknowledged;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: _FilterBar(
            filterType: _filterType,
            filterAcknowledged: _filterAcknowledged,
            onTypeChanged: (v) => setState(() => _filterType = v),
            onAcknowledgedChanged: (v) =>
                setState(() => _filterAcknowledged = v),
          ),
        ),
      ),
      body: _buildFirestoreList(context),
    );
  }

  Widget _buildFirestoreList(BuildContext context) {
    final fb = context.read<FirebaseService>();

    Stream<List<AlertModel>> stream;
    if (_filterAcknowledged == false) {
      stream = fb.getUnacknowledgedAlertsStream();
    } else if (_filterType != null) {
      stream = fb.getAlertsByTypeStream(_filterType!);
    } else {
      stream = fb.getAlertsStream();
    }

    return StreamBuilder<List<AlertModel>>(
      stream: stream,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          // Firestore unavailable — fall back to legacy REST API list
          return _LegacyAlertList(
            filterType: _filterType,
            filterAcknowledged: _filterAcknowledged,
          );
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final alerts = snapshot.data!;
        if (alerts.isEmpty) {
          return const Center(child: Text('No alerts found.'));
        }
        return ListView.builder(
          itemCount: alerts.length,
          itemBuilder: (context, index) {
            final alert = alerts[index];
            return AlertCard(
              alert: alert,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => AlertDetailScreen(alert: alert),
                ),
              ),
            );
          },
        );
      },
    );
  }
}

/// Legacy REST API–backed alert list used when Firestore is unavailable.
class _LegacyAlertList extends StatefulWidget {
  const _LegacyAlertList({
    required this.filterType,
    required this.filterAcknowledged,
  });

  final String? filterType;
  final bool? filterAcknowledged;

  @override
  State<_LegacyAlertList> createState() => _LegacyAlertListState();
}

class _LegacyAlertListState extends State<_LegacyAlertList> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchAlerts());
  }

  Future<void> _fetchAlerts() async {
    await context.read<ApiService>().fetchAlerts(
          activityType: widget.filterType,
          acknowledged: widget.filterAcknowledged,
        );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<ApiService>();

    if (api.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (api.error != null) {
      return Center(child: Text('Error: ${api.error}'));
    }
    if (api.alerts.isEmpty) {
      return const Center(child: Text('No alerts found.'));
    }
    return RefreshIndicator(
      onRefresh: _fetchAlerts,
      child: ListView.builder(
        itemCount: api.alerts.length,
        itemBuilder: (context, index) {
          final alert = api.alerts[index];
          return AlertCard(
            alert: alert,
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => AlertDetailScreen(alert: alert),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.filterType,
    required this.filterAcknowledged,
    required this.onTypeChanged,
    required this.onAcknowledgedChanged,
  });

  final String? filterType;
  final bool? filterAcknowledged;
  final ValueChanged<String?> onTypeChanged;
  final ValueChanged<bool?> onAcknowledgedChanged;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          FilterChip(
            label: const Text('Unacknowledged'),
            selected: filterAcknowledged == false,
            onSelected: (selected) =>
                onAcknowledgedChanged(selected ? false : null),
          ),
          const SizedBox(width: 8),
          ...['weapon', 'concealment', 'loitering'].map(
            (type) => Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Text(type),
                selected: filterType == type,
                onSelected: (selected) =>
                    onTypeChanged(selected ? type : null),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
