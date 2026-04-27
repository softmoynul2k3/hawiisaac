# API Integration Guide

This file explains the 2 app flows:

1. `Content -> Workout -> Logging`
2. `Scan Equipment -> Recommended Workout -> Logging`

The goal is simple:

- user clicks content and logging opens on the first step
- user scans equipment and gets matched workouts
- user picks a workout and logging opens on the first step
- logs always keep the source content when content started the flow

## System 1: Content to Logging

### Step 1: Load content list

`GET /contents`

Example item:

```json
{
  "id": 12,
  "title": "Bodyweight Burn",
  "feed_type": "browse",
  "workout": {
    "id": 7,
    "name": "Body warm-up"
  },
  "summary": "Quick fat-burning bodyweight session.",
  "body": "Long form description here.",
  "image": "https://example.com/image.jpg",
  "video": "https://example.com/video.mp4",
  "is_active": true,
  "created_at": "2026-04-27T08:10:00Z",
  "updated_at": "2026-04-27T08:10:00Z",
  "bookmark_count": 10,
  "share_count": 3,
  "reaction_count": 8,
  "view_count": 42
}
```

Frontend rule:

- if `workout` exists, show `Start Exercise`
- if `workout` is `null`, do not start workout logging from that content

### Step 2: Start log from content

`POST /contents/{content_id}/start-log`

No request body.

Example:

`POST /contents/12/start-log`

Success response:

```json
{
  "session": {
    "id": 25,
    "user_id": "11111111-2222-3333-4444-555555555555",
    "date": "2026-04-27",
    "duration_minutes": 1,
    "created_at": "2026-04-27T09:15:00Z",
    "workout_logs": [
      {
        "id": 70,
        "workout": {
          "id": 7,
          "name": "Body warm-up"
        },
        "content": {
          "id": 12,
          "title": "Bodyweight Burn"
        },
        "note": "Started from content: Bodyweight Burn",
        "set_logs": [],
        "cardio_log": null
      }
    ]
  },
  "first_workout_log": {
    "id": 70,
    "workout": {
      "id": 7,
      "name": "Body warm-up"
    },
    "content": {
      "id": 12,
      "title": "Bodyweight Burn"
    },
    "note": "Started from content: Bodyweight Burn",
    "set_logs": [],
    "cardio_log": null
  }
}
```

Use these fields in the logging screen:

- `session.id`
- `first_workout_log.id`
- `first_workout_log.workout.id`
- `first_workout_log.workout.name`
- `first_workout_log.content.title`

## System 2: Scan Equipment to Logging

### Step 1: Upload equipment image

`POST /scan-equipment-upload`

Request type:

- `multipart/form-data`
- field name: `image`

Success response:

```json
{
  "success": true,
  "equipment_detected": [
    {
      "id": 3,
      "name": "Olympic Barbell",
      "confidence": 0.96,
      "description": "Standard Olympic lifting bar."
    }
  ],
  "primary_equipment": "Olympic Barbell",
  "primary_equipment_id": 3,
  "recommended_workouts": [
    {
      "id": 21,
      "name": "Barbell Bench Press",
      "description": "Classic chest pressing movement.",
      "sets": "5",
      "reps": "8-12",
      "rest": "60-90 sec",
      "banner": "https://example.com/workout-banner.jpg",
      "video": "https://example.com/workout-video.mp4",
      "equipment": {
        "id": 3,
        "name": "Olympic Barbell"
      },
      "category": {
        "id": 2,
        "name": "Strength"
      }
    }
  ],
  "error_message": null
}
```

Frontend usage:

- show `equipment_detected`
- highlight `primary_equipment`
- render `recommended_workouts`
- when user taps one workout, open detail or start log directly

### Step 2: Optional workout details page

`GET /workout/{workout_id}`

Use this if the app needs the full workout detail screen before starting.

### Step 3: Start log from workout

`POST /workout/{workout_id}/start-log`

Optional query:

- `content_id`

Examples:

- `POST /workout/21/start-log`
- `POST /workout/21/start-log?content_id=12`

Success response:

```json
{
  "session": {
    "id": 26,
    "user_id": "11111111-2222-3333-4444-555555555555",
    "date": "2026-04-27",
    "duration_minutes": 1,
    "created_at": "2026-04-27T09:22:00Z",
    "workout_logs": [
      {
        "id": 71,
        "workout": {
          "id": 21,
          "name": "Barbell Bench Press"
        },
        "content": null,
        "note": "Started workout: Barbell Bench Press",
        "set_logs": [],
        "cardio_log": null
      }
    ]
  },
  "first_workout_log": {
    "id": 71,
    "workout": {
      "id": 21,
      "name": "Barbell Bench Press"
    },
    "content": null,
    "note": "Started workout: Barbell Bench Press",
    "set_logs": [],
    "cardio_log": null
  }
}
```

Use these fields in the logging screen:

- `session.id`
- `first_workout_log.id`
- `first_workout_log.workout.id`
- `first_workout_log.workout.name`

## Logging APIs used by both systems

### Add one completed set

`POST /set-log`

```json
{
  "workout_log_id": 70,
  "weight": 0,
  "reps": 45,
  "order": 1,
  "is_completed": true
}
```

Response:

```json
{
  "id": 201,
  "weight": 0,
  "reps": 45,
  "order": 1,
  "is_completed": true,
  "volume": 0,
  "one_rm": 0
}
```

### Add cardio result

`POST /cardio-log`

```json
{
  "workout_log_id": 70,
  "time_minutes": 24.13,
  "distance": 0,
  "speed": 0,
  "incline": 0
}
```

Response:

```json
{
  "id": 15,
  "time_minutes": 24.13,
  "distance": 0,
  "speed": 0,
  "incline": 0
}
```

### Load logs/history

`GET /sessions`

Example item:

```json
{
  "id": 25,
  "user_id": "11111111-2222-3333-4444-555555555555",
  "date": "2026-04-27",
  "duration_minutes": 24,
  "created_at": "2026-04-27T09:15:00Z",
  "workout_logs": [
    {
      "id": 70,
      "workout": {
        "id": 7,
        "name": "Body warm-up"
      },
      "content": {
        "id": 12,
        "title": "Bodyweight Burn"
      },
      "note": "Started from content: Bodyweight Burn",
      "set_logs": [],
      "cardio_log": null
    }
  ]
}
```

Frontend usage:

- show `workout_logs[].workout.name`
- if `workout_logs[].content` exists, show the source content title
- show `set_logs`
- show `cardio_log`

## Recommended frontend order

### Flow A: Content

1. `GET /contents`
2. user taps content
3. `POST /contents/{content_id}/start-log`
4. open logging screen with `first_workout_log`
5. save progress using `/set-log` or `/cardio-log`
6. load history using `GET /sessions`

### Flow B: Equipment scan

1. `POST /scan-equipment-upload`
2. show `recommended_workouts`
3. user taps one workout
4. optional `GET /workout/{workout_id}`
5. `POST /workout/{workout_id}/start-log`
6. open logging screen with `first_workout_log`
7. save progress using `/set-log` or `/cardio-log`
8. load history using `GET /sessions`

## Important error cases

### Content flow

- `404 Content not found`
- `400 This content is not linked to any workout`

### Workout flow

- `404 Workout not found`
- `404 Content not found`
- `400 Selected workout does not match the linked content workout`

### Set log

- `404 Workout log not found`
- `400 Set order already exists for this workout log`

### Cardio log

- `404 Workout log not found`
- `400 Cardio log already exists for this workout log`

### Equipment scan

- `success=false` if image processing fails
- `success=true` with empty `recommended_workouts` if no matching equipment is found in DB

## Final recommendation

For best frontend integration:

- use `POST /contents/{content_id}/start-log` for content cards
- use `POST /scan-equipment-upload` to get equipment matches and recommended workouts
- use `POST /workout/{workout_id}/start-log` for workout cards from equipment scan
- use `POST /set-log`, `POST /cardio-log`, and `GET /sessions` for the shared logging system

This setup now supports both screens in your designs with a clean and direct API flow.
