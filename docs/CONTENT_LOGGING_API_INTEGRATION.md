# Workout System API

This document only covers the workout system.

The workout system now works in 2 entry flows:

1. `Scan Equipment -> Select Workout -> Start Session`
2. `Content -> Multiple Workouts -> Start Session -> Complete One By One`

## Core design

- a user creates one `session`
- one session contains one or many ordered `session workouts`
- each session workout points to one workout
- workout type decides logging rule:
  - `cardio` uses `cardio-log`
  - `non_cardio` uses `set-log`
- calories are calculated from `workout.met_value`, workout time, and `user_weight_kg`
- `WorkoutLog` is removed from the system

## Workout model

Each workout now includes:

- `workout_type`: `cardio` or `non_cardio`
- `met_value`: number used for calorie calculation

Example workout:

```json
{
  "id": 21,
  "name": "Barbell Bench Press",
  "workout_type": "non_cardio",
  "met_value": 5.0,
  "sets": "4",
  "reps": "8-12",
  "rest": "60-90 sec"
}
```

## Session model

One session can contain many workouts.

Example response shape:

```json
{
  "id": 25,
  "user_id": "11111111-2222-3333-4444-555555555555",
  "date": "2026-04-28",
  "duration_minutes": 24,
  "note": "Upper body day",
  "user_weight_kg": 72,
  "status": "active",
  "total_calories_burned": 164.52,
  "created_at": "2026-04-28T09:15:00Z",
  "updated_at": "2026-04-28T09:22:00Z",
  "completed_at": null,
  "workouts": [
    {
      "id": 70,
      "order": 1,
      "workout": {
        "id": 21,
        "name": "Barbell Bench Press",
        "workout_type": "non_cardio",
        "met_value": 5.0,
        "sets": "4",
        "reps": "8-12",
        "rest": "60-90 sec"
      },
      "content": null,
      "note": "Started workout: Barbell Bench Press",
      "is_completed": false,
      "estimated_calories_burned": 38.52,
      "actual_calories_burned": 0,
      "set_logs": [],
      "cardio_log": null
    }
  ]
}
```

## Create a session directly

`POST /sessions`

Use this when the app wants to create a session with one or many workouts manually.

```json
{
  "date": "2026-04-28",
  "duration_minutes": 0,
  "note": "Mixed workout",
  "user_weight_kg": 72,
  "workouts": [
    {
      "workout_id": 21,
      "note": "Bench first",
      "order": 1
    },
    {
      "workout_id": 33,
      "note": "Finish with treadmill",
      "order": 2
    }
  ]
}
```

## Flow 1: Start from content

### Start session from content

`POST /contents/{content_id}/start-log`

Rules:

- content may have multiple workouts
- backend creates one session
- backend creates one ordered session workout for each linked workout
- frontend should open the first workout and then move to next by `order`

Example response:

```json
{
  "session": {
    "id": 30,
    "user_id": "11111111-2222-3333-4444-555555555555",
    "date": "2026-04-28",
    "duration_minutes": 1,
    "note": null,
    "user_weight_kg": null,
    "status": "active",
    "total_calories_burned": 0,
    "created_at": "2026-04-28T10:00:00Z",
    "updated_at": "2026-04-28T10:00:00Z",
    "completed_at": null,
    "workouts": [
      {
        "id": 81,
        "order": 1,
        "workout": {
          "id": 7,
          "name": "Body warm-up",
          "workout_type": "non_cardio",
          "met_value": 4.5,
          "sets": "1",
          "reps": "45 sec",
          "rest": "0"
        },
        "content": {
          "id": 12,
          "title": "Bodyweight Burn"
        },
        "note": "Started from content: Bodyweight Burn",
        "is_completed": false,
        "estimated_calories_burned": 0,
        "actual_calories_burned": 0,
        "set_logs": [],
        "cardio_log": null
      },
      {
        "id": 82,
        "order": 2,
        "workout": {
          "id": 8,
          "name": "Push-Up",
          "workout_type": "non_cardio",
          "met_value": 5.0,
          "sets": "3",
          "reps": "12",
          "rest": "30 sec"
        },
        "content": {
          "id": 12,
          "title": "Bodyweight Burn"
        },
        "note": "Started from content: Bodyweight Burn",
        "is_completed": false,
        "estimated_calories_burned": 0,
        "actual_calories_burned": 0,
        "set_logs": [],
        "cardio_log": null
      }
    ]
  },
  "first_session_workout": {
    "id": 81,
    "order": 1,
    "workout": {
      "id": 7,
      "name": "Body warm-up",
      "workout_type": "non_cardio",
      "met_value": 4.5,
      "sets": "1",
      "reps": "45 sec",
      "rest": "0"
    },
    "content": {
      "id": 12,
      "title": "Bodyweight Burn"
    },
    "note": "Started from content: Bodyweight Burn",
    "is_completed": false,
    "estimated_calories_burned": 0,
    "actual_calories_burned": 0,
    "set_logs": [],
    "cardio_log": null
  }
}
```

## Flow 2: Start from equipment scan

### Scan equipment

`POST /scan-equipment-upload`

The scan result returns recommended workouts.

### Start session from one selected workout

`POST /workout/{workout_id}/start-log`

Optional query:

- `content_id`

Example response:

```json
{
  "session": {
    "id": 31,
    "user_id": "11111111-2222-3333-4444-555555555555",
    "date": "2026-04-28",
    "duration_minutes": 1,
    "note": null,
    "user_weight_kg": null,
    "status": "active",
    "total_calories_burned": 0,
    "created_at": "2026-04-28T10:10:00Z",
    "updated_at": "2026-04-28T10:10:00Z",
    "completed_at": null,
    "workouts": [
      {
        "id": 83,
        "order": 1,
        "workout": {
          "id": 21,
          "name": "Barbell Bench Press",
          "workout_type": "non_cardio",
          "met_value": 5.0,
          "sets": "4",
          "reps": "8-12",
          "rest": "60-90 sec"
        },
        "content": null,
        "note": "Started workout: Barbell Bench Press",
        "is_completed": false,
        "estimated_calories_burned": 0,
        "actual_calories_burned": 0,
        "set_logs": [],
        "cardio_log": null
      }
    ]
  },
  "first_session_workout": {
    "id": 83,
    "order": 1,
    "workout": {
      "id": 21,
      "name": "Barbell Bench Press",
      "workout_type": "non_cardio",
      "met_value": 5.0,
      "sets": "4",
      "reps": "8-12",
      "rest": "60-90 sec"
    },
    "content": null,
    "note": "Started workout: Barbell Bench Press",
    "is_completed": false,
    "estimated_calories_burned": 0,
    "actual_calories_burned": 0,
    "set_logs": [],
    "cardio_log": null
  }
}
```

## Add another workout to an existing session

`POST /sessions/{session_id}/workouts`

```json
{
  "session_id": 31,
  "workout_id": 33,
  "content_id": null,
  "note": "Finish with treadmill",
  "order": 2
}
```

## Non-cardio logging

Use `set-log` only when `workout.workout_type = non_cardio`.

`POST /set-log`

```json
{
  "session_workout_id": 83,
  "weight": 60,
  "reps": 10,
  "order": 1,
  "duration_seconds": 45,
  "is_completed": true
}
```

Response:

```json
{
  "id": 201,
  "weight": 60,
  "reps": 10,
  "order": 1,
  "duration_seconds": 45,
  "is_completed": true,
  "volume": 600,
  "one_rm": 80
}
```

Calories for non-cardio are estimated from:

- `sum(set_log.duration_seconds)`
- `workout.met_value`
- `session.user_weight_kg` or default `70kg`

## Cardio logging

Use `cardio-log` only when `workout.workout_type = cardio`.

`POST /cardio-log`

```json
{
  "session_workout_id": 90,
  "time_minutes": 24.13,
  "distance": 4.2,
  "speed": 10.4,
  "incline": 1.5,
  "user_weight_kg": 72
}
```

Response:

```json
{
  "id": 15,
  "time_minutes": 24.13,
  "distance": 4.2,
  "speed": 10.4,
  "incline": 1.5,
  "calories_burned": 213.77,
  "user_weight_kg": 72
}
```

Calories for cardio are calculated from:

- `workout.met_value`
- `time_minutes`
- `user_weight_kg`

Formula:

- `calories = (MET * 3.5 * weight_kg / 200) * minutes`

## Mark one workout complete

`POST /session-workouts/{session_workout_id}/complete`

```json
{
  "note": "Done",
  "mark_session_complete_if_finished": true
}
```

## Mark full session complete

`POST /sessions/{session_id}/complete`

```json
{
  "duration_minutes": 28,
  "note": "Finished all workouts"
}
```

## Session history

### List sessions

`GET /sessions`

### Get one session

`GET /sessions/{session_id}`

Frontend should use:

- `session.workouts`
- `workouts[].order`
- `workouts[].is_completed`
- `workouts[].set_logs`
- `workouts[].cardio_log`
- `session.total_calories_burned`

## Important validation rules

- content start requires at least one linked workout
- selected workout must belong to content when `content_id` is sent
- `set-log` is rejected for `cardio` workouts
- `cardio-log` is rejected for `non_cardio` workouts
- `cardio-log` allows only one cardio result per session workout
- set order must be unique inside the same session workout

## Important error cases

- `404 Content not found`
- `404 Workout not found`
- `404 Workout session not found`
- `404 Session workout not found`
- `400 This content is not linked to any workouts`
- `400 Selected workout does not match the linked content workouts`
- `400 Set logs are only allowed for non-cardio workouts`
- `400 Cardio logs are only allowed for cardio workouts`
- `400 Cardio log already exists for this session workout`
- `400 Set order already exists for this session workout`

## Frontend flow summary

### Content flow

1. load content
2. call `POST /contents/{content_id}/start-log`
3. open `first_session_workout`
4. save each workout using `POST /set-log` or `POST /cardio-log`
5. call `POST /session-workouts/{id}/complete`
6. move to next workout by `order`
7. finish with `POST /sessions/{session_id}/complete`

### Equipment flow

1. call `POST /scan-equipment-upload`
2. show recommended workouts
3. call `POST /workout/{workout_id}/start-log`
4. open `first_session_workout`
5. save logs
6. complete workout
7. complete session
