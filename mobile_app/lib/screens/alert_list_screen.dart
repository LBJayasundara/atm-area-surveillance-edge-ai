import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/alert_model.dart';
import '../services/api_service.dart';
import '../widgets/alert_card.dart';
import 'alert_detail_screen.dart';

/// Scrollable list of alerts with filter chips.
class AlertListScreen extends StatefulWidget {
  const AlertListScreen({super.key});

  @override
  State<AlertListScreen> createState() => _AlertListScreenState();
}

class _AlertListScreenState extends State<AlertListScreen> {
  String? _filterType;
  bool? _filterAcknowledged;

  static const _filterOptions = ['weapon', 'concealment', 'loitering'];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fetchAlerts());
  }

  Future<void> _fetchAlerts() async {
    await context.read<ApiService>().fetchAlerts(
          activityType: _filterType,
          acknowledged: _filterAcknowledged,
        );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<ApiService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchAlerts,
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: _FilterBar(
            filterType: _filterType,
            filterAcknowledged: _filterAcknowledged,
            onTypeChanged: (v) {
              setState(() => _filterType = v);
              _fetchAlerts();
            },
            onAcknowledgedChanged: (v) {
              setState(() => _filterAcknowledged = v);
              _fetchAlerts();
            },
          ),
        ),
      ),
      body: _buildBody(api),
    );
  }

  Widget _buildBody(ApiService api) {
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
