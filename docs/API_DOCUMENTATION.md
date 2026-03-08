# API Documentation

Base URL: `http://<raspberry-pi-ip>:5000`

## Authentication

All endpoints except `/health` require the `X-Auth-Token` header:

```
X-Auth-Token: <your-token>
```

Configure the token in `config/config.yaml` → `api.auth_token`.

---

## Endpoints

### GET /health

Returns system health. No authentication required.

**Response 200:**
```json
{ "status": "ok", "service": "atm-surveillance" }
```

---

### GET /alerts

List alerts with optional filters.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max records (≤ 200) |
| `offset` | int | 0 | Pagination offset |
| `activity_type` | string | — | Filter: `weapon`, `concealment`, `loitering` |
| `acknowledged` | bool | — | Filter: `true` / `false` |

**Response 200:**
```json
{
  "alerts": [
    {
      "id": "alert_20260308_143218_001",
      "activity": "Weapon Detected",
      "activity_type": "weapon",
      "detected_object": "gun",
      "confidence": 0.91,
      "timestamp": "2026-03-08T14:32:18Z",
      "location": "ATM Entrance",
      "image": "snapshot_20260308_143218_001.jpg",
      "acknowledged": false,
      "metadata": {
        "person_id": null,
        "bounding_box": [120, 230, 180, 310],
        "zone": "restricted_atm_zone",
        "camera_id": "cam_01"
      }
    }
  ],
  "count": 1
}
```

---

### GET /alerts/image/\<filename\>

Serve a snapshot image.

**Response 200:** JPEG image binary  
**Response 404:** `{ "error": "Image not found" }`

---

### POST /alerts/acknowledge

Mark an alert as acknowledged.

**Request Body:**
```json
{ "alert_id": "alert_20260308_143218_001" }
```

**Response 200:**
```json
{ "message": "Alert alert_20260308_143218_001 acknowledged." }
```

**Response 404:** Alert not found  
**Response 400:** Missing `alert_id`

---

### GET /stats

Return alert statistics.

**Response 200:**
```json
{
  "total_alerts": 42,
  "unacknowledged_alerts": 5,
  "by_activity_type": {
    "weapon": 10,
    "concealment": 15,
    "loitering": 17
  }
}
```

---

### GET /zones

List configured monitoring zones.

**Response 200:**
```json
{
  "zones": [
    {
      "name": "restricted_atm_zone",
      "zone_type": "restricted",
      "description": "Main ATM alcove",
      "polygon": [[100, 200], [540, 200], [540, 680], [100, 680]]
    }
  ]
}
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorised (invalid or missing token) |
| 404 | Resource not found |
| 500 | Internal server error |
