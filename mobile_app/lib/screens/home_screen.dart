import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../utils/constants.dart';

/// Dashboard screen showing system statistics and connection status.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _apiOnline = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refresh());
  }

  Future<void> _refresh() async {
    final api = context.read<ApiService>();
    await api.fetchStats();
    final online = await api.checkHealth();
    if (mounted) setState(() => _apiOnline = online);
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<ApiService>();
    final stats = api.stats;

    return Scaffold(
      appBar: AppBar(
        title: const Text(AppConstants.appName),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _StatusCard(online: _apiOnline),
            const SizedBox(height: 16),
            _StatsGrid(stats: stats),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.online});

  final bool online;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(
          online ? Icons.videocam : Icons.videocam_off,
          color: online ? Colors.green : Colors.red,
          size: 36,
        ),
        title: Text(online ? 'System Online' : 'System Offline'),
        subtitle: Text(online ? 'Surveillance active' : 'Cannot reach API'),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({required this.stats});

  final Map<String, dynamic> stats;

  @override
  Widget build(BuildContext context) {
    final total = stats['total_alerts'] ?? 0;
    final unacked = stats['unacknowledged_alerts'] ?? 0;
    final byType = (stats['by_activity_type'] as Map?)?.cast<String, dynamic>() ?? {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Statistics', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(child: _StatTile(label: 'Total Alerts', value: '$total')),
            const SizedBox(width: 8),
            Expanded(
              child: _StatTile(
                label: 'Unacknowledged',
                value: '$unacked',
                color: unacked > 0 ? Colors.orange : null,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (byType.isNotEmpty) ...[
          Text('By Type', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          ...byType.entries.map(
            (e) => ListTile(
              dense: true,
              leading: const Icon(Icons.label, size: 20),
              title: Text(e.key),
              trailing: Text('${e.value}'),
            ),
          ),
        ],
      ],
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, this.color});

  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              value,
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: color,
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 4),
            Text(label, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}
