import 'package:flutter/foundation.dart';

/// Data model representing a single surveillance alert.
@immutable
class AlertModel {
  const AlertModel({
    required this.id,
    required this.activity,
    required this.activityType,
    required this.detectedObject,
    required this.confidence,
    required this.timestamp,
    required this.location,
    required this.image,
    required this.acknowledged,
    required this.metadata,
  });

  final String id;
  final String activity;
  final String activityType;
  final String detectedObject;
  final double confidence;
  final DateTime timestamp;
  final String location;
  final String image;
  final bool acknowledged;
  final Map<String, dynamic> metadata;

  factory AlertModel.fromJson(Map<String, dynamic> json) {
    return AlertModel(
      id: json['id'] as String? ?? '',
      activity: json['activity'] as String? ?? '',
      activityType: json['activity_type'] as String? ?? '',
      detectedObject: json['detected_object'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ??
          DateTime.now(),
      location: json['location'] as String? ?? '',
      image: json['image'] as String? ?? '',
      acknowledged: json['acknowledged'] as bool? ?? false,
      metadata: (json['metadata'] as Map<String, dynamic>?) ?? {},
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'activity': activity,
        'activity_type': activityType,
        'detected_object': detectedObject,
        'confidence': confidence,
        'timestamp': timestamp.toIso8601String(),
        'location': location,
        'image': image,
        'acknowledged': acknowledged,
        'metadata': metadata,
      };

  AlertModel copyWith({bool? acknowledged}) => AlertModel(
        id: id,
        activity: activity,
        activityType: activityType,
        detectedObject: detectedObject,
        confidence: confidence,
        timestamp: timestamp,
        location: location,
        image: image,
        acknowledged: acknowledged ?? this.acknowledged,
        metadata: metadata,
      );
}
