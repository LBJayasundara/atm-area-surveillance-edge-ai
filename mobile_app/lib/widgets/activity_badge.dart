import 'package:flutter/material.dart';

/// Colour-coded badge indicating the type of suspicious activity.
class ActivityBadge extends StatelessWidget {
  const ActivityBadge({
    super.key,
    required this.activityType,
    this.compact = false,
  });

  final String activityType;
  final bool compact;

  static const _config = {
    'weapon': (Icons.gavel, Color(0xFFD32F2F), 'WEAPON'),
    'concealment': (Icons.face_retouching_off, Color(0xFFE65100), 'FACE'),
    'loitering': (Icons.directions_walk, Color(0xFF1565C0), 'LOITER'),
  };

  @override
  Widget build(BuildContext context) {
    final entry = _config[activityType.toLowerCase()] ??
        (Icons.warning_amber, Colors.grey, activityType.toUpperCase());

    final icon = entry.$1 as IconData;
    final color = entry.$2 as Color;
    final label = entry.$3 as String;

    if (compact) {
      return Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: color, size: 24),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
              letterSpacing: 1,
            ),
          ),
        ],
      ),
    );
  }
}
