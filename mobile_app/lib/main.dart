import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/api_service.dart';
import 'services/firebase_service.dart';
import 'services/notification_service.dart';
import 'screens/home_screen.dart';
import 'screens/alert_list_screen.dart';
import 'screens/settings_screen.dart';
import 'utils/constants.dart';

/// Background FCM message handler — must be a top-level function annotated
/// with `@pragma('vm:entry-point')` so it can be invoked from an isolate.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialise Firebase — requires google-services.json (Android) or
  // GoogleService-Info.plist (iOS) to be present in the project.
  await Firebase.initializeApp();

  // Subscribe to the ATM alerts FCM topic.
  await FirebaseMessaging.instance.subscribeToTopic(
    AppConstants.fcmAlertsTopic,
  );

  // Register background message handler.
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // Initialise local notification plugin (used for foreground FCM messages).
  await NotificationService.instance.init();

  runApp(const ATMSurveillanceApp());
}

class ATMSurveillanceApp extends StatelessWidget {
  const ATMSurveillanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ApiService()),
        Provider(create: (_) => FirebaseService()),
      ],
      child: MaterialApp(
        title: AppConstants.appName,
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: AppConstants.primaryColor),
          useMaterial3: true,
          appBarTheme: const AppBarTheme(centerTitle: true),
        ),
        home: const MainNavigation(),
      ),
    );
  }
}

class MainNavigation extends StatefulWidget {
  const MainNavigation({super.key});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _selectedIndex = 0;

  static const List<Widget> _screens = [
    HomeScreen(),
    AlertListScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dashboard'),
          NavigationDestination(icon: Icon(Icons.notifications), label: 'Alerts'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}
