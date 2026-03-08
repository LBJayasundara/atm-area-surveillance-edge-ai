import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';

/// Data model representing a single surveillance alert.
///
/// Supports both the legacy REST API JSON format and the Firebase Firestore
/// document format so both data sources can share the same model.
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
    required this.imageUrl,
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

  /// Local snapshot filename (REST API / SQLite backend).
  final String image;

  /// Firebase Storage public URL (Firebase backend).
  final String imageUrl;

  final bool acknowledged;
  final Map<String, dynamic> metadata;

  // ---------------------------------------------------------------------------
  // Factory constructors
  // ---------------------------------------------------------------------------

  /// Create an [AlertModel] from a REST API JSON response.
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
      imageUrl: json['image_url'] as String? ?? '',
      acknowledged: json['acknowledged'] as bool? ?? false,
      metadata: (json['metadata'] as Map<String, dynamic>?) ?? {},
    );
  }

  /// Create an [AlertModel] from a Firestore [DocumentSnapshot].
  factory AlertModel.fromFirestore(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>? ?? {};
    return AlertModel(
      id: doc.id,
      activity: data['activity'] as String? ?? '',
      activityType: data['activity_type'] as String? ?? '',
      detectedObject: data['detected_object'] as String? ?? '',
      confidence: (data['confidence'] as num?)?.toDouble() ?? 0.0,
      timestamp: data['timestamp'] is Timestamp
          ? (data['timestamp'] as Timestamp).toDate()
          : DateTime.now(),
      location: data['location'] as String? ?? '',
      image: '',
      imageUrl: data['image_url'] as String? ?? '',
      acknowledged: data['acknowledged'] as bool? ?? false,
      metadata: (data['metadata'] as Map<String, dynamic>?) ?? {},
    );
  }

  // ---------------------------------------------------------------------------
  // Serialisation
  // ---------------------------------------------------------------------------

  Map<String, dynamic> toJson() => {
        'id': id,
        'activity': activity,
        'activity_type': activityType,
        'detected_object': detectedObject,
        'confidence': confidence,
        'timestamp': timestamp.toIso8601String(),
        'location': location,
        'image': image,
        'image_url': imageUrl,
        'acknowledged': acknowledged,
        'metadata': metadata,
      };

  Map<String, dynamic> toFirestore() => {
        'alert_id': id,
        'activity': activity,
        'activity_type': activityType,
        'detected_object': detectedObject,
        'confidence': confidence,
        'timestamp': Timestamp.fromDate(timestamp),
        'location': location,
        'image_url': imageUrl,
        'acknowledged': acknowledged,
        'metadata': metadata,
      };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /// Returns the best available image URL for display.
  ///
  /// Prefers [imageUrl] (Firebase Storage) when set, otherwise falls back to
  /// the local [image] filename.
  String get displayImageUrl => imageUrl.isNotEmpty ? imageUrl : image;

  AlertModel copyWith({bool? acknowledged}) => AlertModel(
        id: id,
        activity: activity,
        activityType: activityType,
        detectedObject: detectedObject,
        confidence: confidence,
        timestamp: timestamp,
        location: location,
        image: image,
        imageUrl: imageUrl,
        acknowledged: acknowledged ?? this.acknowledged,
        metadata: metadata,
      );
}
