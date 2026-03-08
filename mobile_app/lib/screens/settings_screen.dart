import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../utils/constants.dart';

/// Settings screen for configuring API URL and auth token.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;
  late TextEditingController _tokenController;
  bool _obscureToken = true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final api = context.read<ApiService>();
    _urlController = TextEditingController(text: api.baseUrl);
    _tokenController = TextEditingController(text: api.authToken);
  }

  @override
  void dispose() {
    _urlController.dispose();
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final api = context.read<ApiService>();
    await api.updateSettings(
      baseUrl: _urlController.text.trim(),
      authToken: _tokenController.text.trim(),
    );
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings saved.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('API Configuration',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'API Base URL',
              hintText: 'http://192.168.1.100:5000',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.link),
            ),
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _tokenController,
            obscureText: _obscureToken,
            decoration: InputDecoration(
              labelText: 'Auth Token',
              border: const OutlineInputBorder(),
              prefixIcon: const Icon(Icons.key),
              suffixIcon: IconButton(
                icon: Icon(
                    _obscureToken ? Icons.visibility : Icons.visibility_off),
                onPressed: () =>
                    setState(() => _obscureToken = !_obscureToken),
              ),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            icon: const Icon(Icons.save),
            label: const Text('Save Settings'),
            onPressed: _save,
          ),
          const SizedBox(height: 24),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('App Version'),
            trailing: Text(AppConstants.appVersion),
          ),
          ListTile(
            leading: const Icon(Icons.code),
            title: const Text('Source Code'),
            subtitle: const Text(
                'github.com/LBJayasundara/atm-area-surveillance-edge-ai'),
          ),
        ],
      ),
    );
  }
}
