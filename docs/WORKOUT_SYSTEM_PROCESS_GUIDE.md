# Workout System Process Guide

This file explains only how the workout system works in app flow.

There are 2 ways a user starts workout:

1. `Scan equipment -> select workout -> start session`
2. `Click content -> content has multiple workouts -> start session -> complete one by one`

## Main idea

- one user creates one `session`
- one session can contain one or many `workouts`
- each workout inside session is a `session_workout`
- only one `active` session is allowed per user
- if workout type is `non_cardio`, save progress with `POST /set-log`
- if workout type is `cardio`, save progress with `POST /cardio-log`

## App open / resume flow

Frontend should first call:

`GET /sessions/active`

If active session exists:

- backend returns the active session
- backend returns the current workout as `current_session_workout`
- backend resumes from `current_workout_order`

If no active session exists:

- backend returns `404 Active session not found`

## Flow 1: Scan equipment -> select workout

### Step 1: Scan equipment

Frontend calls:

`POST /scan-equipment-upload`

Response example:

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
      "workout_type": "non_cardio",
      "met_value": 5.0,
      "sets": "4",
      "reps": "8-12",
      "rest": "60-90 sec"
    }
  ]
}
```

### Step 2: User selects one workout

Frontend calls:

`POST /workout/{workout_id}/start-log`

Example:

`POST /workout/21/start-log`

Before creating new session:

- backend checks existing active session
- if active session exists, backend returns that existing session instead of creating new one

Response example:

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

### Step 3: Add log for selected workout

If `workout_type = non_cardio`, use:

`POST /set-log`

Example:

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

If same `session_workout_id` + same `order` is sent again:

- backend updates existing set log
- backend does not create duplicate log

If `workout_type = cardio`, use:

`POST /cardio-log`

Example:

```json
{
  "session_workout_id": 83,
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

If cardio log already exists for that `session_workout_id`:

- backend updates the existing cardio log
- backend does not create duplicate cardio log

### Step 4: Mark workout complete

Frontend calls:

`POST /session-workouts/{session_workout_id}/complete`

Example:

```json
{
  "note": "Done",
  "mark_session_complete_if_finished": true
}
```

Backend validation before complete:

- if workout is `non_cardio`, at least 1 set log must exist
- if workout is `cardio`, cardio log must exist
- if no logs exist, backend rejects with `Cannot complete workout without logs`

### Step 5: Finish session

Frontend calls:

`POST /sessions/{session_id}/complete`

Example:

```json
{
  "duration_minutes": 28,
  "note": "Finished workout"
}
```

Backend validation before log create or workout complete:

- backend fetches session from `session_workout_id`
- if `session.status != active`
- reject with `Session is already completed`

## Flow 2: Click content -> multiple workouts

### Step 1: User clicks content

Content already has many linked workouts.

Frontend calls:

`POST /contents/{content_id}/start-log`

Example:

`POST /contents/12/start-log`

Before creating new session:

- backend checks existing active session
- if active session exists, backend returns that existing session instead of creating new one

Response example:

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

### Step 2: Open first workout

Frontend should open:

- `first_session_workout`

Also keep:

- `session.id`
- `session.workouts`

### Step 3: Add logs to first workout

For non-cardio:

`POST /set-log`

```json
{
  "session_workout_id": 81,
  "weight": 0,
  "reps": 45,
  "order": 1,
  "duration_seconds": 45,
  "is_completed": true
}
```

For cardio:

`POST /cardio-log`

```json
{
  "session_workout_id": 81,
  "time_minutes": 10,
  "distance": 2.1,
  "speed": 12.6,
  "incline": 0,
  "user_weight_kg": 72
}
```

### Step 4: Complete first workout

`POST /session-workouts/81/complete`

```json
{
  "note": "First workout done",
  "mark_session_complete_if_finished": true
}
```

### Step 5: Move to next workout

Frontend finds next item from:

- `session.workouts`
- next one by `order`

Example:

- after workout `order = 1`
- move to workout `order = 2`

Then add logs again using `session_workout_id` of that next item.

### Step 6: Finish full session

After all workouts are done:

`POST /sessions/{session_id}/complete`

```json
{
  "duration_minutes": 35,
  "note": "Completed all content workouts"
}
```

## Manual create session example

If frontend wants to create a session directly with many workouts:

`POST /sessions`

```json
{
  "date": "2026-04-28",
  "duration_minutes": 0,
  "note": "Mixed session",
  "user_weight_kg": 72,
  "workouts": [
    {
      "workout_id": 21,
      "note": "Bench first",
      "order": 1
    },
    {
      "workout_id": 33,
      "note": "Treadmill last",
      "order": 2
    }
  ]
}
```

If user already has active session:

- backend returns that active session
- backend does not create a second active session

## Simple frontend rule

- use `first_session_workout` to open first screen
- on app open call `GET /sessions/active`
- use `session.workouts` to know all remaining workouts
- use `session.current_workout_order` to resume current workout
- use `set-log` only for `non_cardio`
- use `cardio-log` only for `cardio`
- after each workout, call complete API
- after all workouts, call session complete API
