from datetime import date, timedelta

from tortoise.transactions import in_transaction

from applications.equipments.models import Workout
from applications.session.models import CardioLog, SetLog, WorkoutLog, WorkoutSession
from applications.user.models import User


SESSION_DATA = [
    {
        "email": "user1@gmail.com",
        "sessions": [
            {
                "date": date.today() - timedelta(days=12),
                "duration_minutes": 58,
                "logs": [
                    {
                        "workout": "Olympic Barbell",
                        "note": "Earlier baseline strength day.",
                        "sets": [
                            {"weight": 55.0, "reps": 8, "order": 1, "is_completed": True},
                            {"weight": 65.0, "reps": 6, "order": 2, "is_completed": True},
                            {"weight": 70.0, "reps": 5, "order": 3, "is_completed": True},
                        ],
                    },
                    {
                        "workout": "Adjustable Dumbbells",
                        "note": "Baseline accessory session.",
                        "sets": [
                            {"weight": 17.5, "reps": 12, "order": 1, "is_completed": True},
                            {"weight": 20.0, "reps": 10, "order": 2, "is_completed": True},
                            {"weight": 20.0, "reps": 9, "order": 3, "is_completed": True},
                        ],
                    },
                ],
            },
            {
                "date": date.today() - timedelta(days=6),
                "duration_minutes": 62,
                "logs": [
                    {
                        "workout": "Olympic Barbell",
                        "note": "Focused on form and steady bar speed.",
                        "sets": [
                            {"weight": 60.0, "reps": 8, "order": 1, "is_completed": True},
                            {"weight": 70.0, "reps": 6, "order": 2, "is_completed": True},
                            {"weight": 75.0, "reps": 5, "order": 3, "is_completed": True},
                        ],
                    },
                    {
                        "workout": "Adjustable Dumbbells",
                        "note": "Accessory work to finish upper body.",
                        "sets": [
                            {"weight": 20.0, "reps": 12, "order": 1, "is_completed": True},
                            {"weight": 22.5, "reps": 10, "order": 2, "is_completed": True},
                            {"weight": 22.5, "reps": 9, "order": 3, "is_completed": True},
                        ],
                    },
                ],
            },
            {
                "date": date.today() - timedelta(days=3),
                "duration_minutes": 38,
                "logs": [
                    {
                        "workout": "Treadmill",
                        "note": "Easy zone 2 cardio.",
                        "cardio": {
                            "time_minutes": 30.0,
                            "distance": 4.2,
                            "speed": 8.4,
                            "incline": 1.5,
                        },
                    }
                ],
            },
        ],
    },
    {
        "email": "user2@gmail.com",
        "sessions": [
            {
                "date": date.today() - timedelta(days=10),
                "duration_minutes": 50,
                "logs": [
                    {
                        "workout": "Leg Press Machine",
                        "note": "Previous lower-body benchmark.",
                        "sets": [
                            {"weight": 90.0, "reps": 12, "order": 1, "is_completed": True},
                            {"weight": 110.0, "reps": 10, "order": 2, "is_completed": True},
                            {"weight": 120.0, "reps": 8, "order": 3, "is_completed": True},
                        ],
                    }
                ],
            },
            {
                "date": date.today() - timedelta(days=5),
                "duration_minutes": 55,
                "logs": [
                    {
                        "workout": "Leg Press Machine",
                        "note": "Controlled tempo throughout.",
                        "sets": [
                            {"weight": 100.0, "reps": 12, "order": 1, "is_completed": True},
                            {"weight": 120.0, "reps": 10, "order": 2, "is_completed": True},
                            {"weight": 130.0, "reps": 8, "order": 3, "is_completed": True},
                        ],
                    },
                    {
                        "workout": "Leg Curl Machine",
                        "note": "Hamstring finisher.",
                        "sets": [
                            {"weight": 35.0, "reps": 15, "order": 1, "is_completed": True},
                            {"weight": 40.0, "reps": 12, "order": 2, "is_completed": True},
                        ],
                    },
                ],
            },
            {
                "date": date.today() - timedelta(days=1),
                "duration_minutes": 42,
                "logs": [
                    {
                        "workout": "Rowing Machine",
                        "note": "Intervals with moderate pace.",
                        "cardio": {
                            "time_minutes": 24.0,
                            "distance": 5.1,
                            "speed": 12.8,
                            "incline": 0.0,
                        },
                    },
                    {
                        "workout": "Ab Wheel",
                        "note": "Core finisher.",
                        "sets": [
                            {"weight": 0.0, "reps": 12, "order": 1, "is_completed": True},
                            {"weight": 0.0, "reps": 10, "order": 2, "is_completed": True},
                        ],
                    },
                ],
            },
        ],
    },
]


async def create_test_sessions():
    session_created = 0
    workout_log_created = 0
    set_log_created = 0
    cardio_log_created = 0

    try:
        async with in_transaction() as conn:
            users = await User.filter(email__in=[item["email"] for item in SESSION_DATA]).using_db(conn)
            users_by_email = {user.email: user for user in users}

            workout_names = [
                log["workout"]
                for user_item in SESSION_DATA
                for session_item in user_item["sessions"]
                for log in session_item["logs"]
            ]
            workouts = await Workout.filter(name__in=workout_names).using_db(conn)
            workouts_by_name = {workout.name: workout for workout in workouts}

            for user_item in SESSION_DATA:
                user = users_by_email.get(user_item["email"])
                if not user:
                    print(f"[dummy-session] skipped missing user: {user_item['email']}")
                    continue

                for session_item in user_item["sessions"]:
                    session, created = await WorkoutSession.get_or_create(
                        user=user,
                        date=session_item["date"],
                        defaults={"duration_minutes": session_item["duration_minutes"]},
                        using_db=conn,
                    )

                    if created:
                        session_created += 1
                    elif session.duration_minutes != session_item["duration_minutes"]:
                        session.duration_minutes = session_item["duration_minutes"]
                        await session.save(using_db=conn)

                    for log_item in session_item["logs"]:
                        workout = workouts_by_name.get(log_item["workout"])
                        if not workout:
                            print(f"[dummy-session] skipped missing workout: {log_item['workout']}")
                            continue

                        workout_log, log_created = await WorkoutLog.get_or_create(
                            session=session,
                            workout=workout,
                            defaults={"note": log_item.get("note")},
                            using_db=conn,
                        )

                        if log_created:
                            workout_log_created += 1
                        elif workout_log.note != log_item.get("note"):
                            workout_log.note = log_item.get("note")
                            await workout_log.save(using_db=conn)

                        for set_item in log_item.get("sets", []):
                            set_log, set_created = await SetLog.get_or_create(
                                workout_log=workout_log,
                                order=set_item["order"],
                                defaults={
                                    "weight": set_item["weight"],
                                    "reps": set_item["reps"],
                                    "is_completed": set_item["is_completed"],
                                },
                                using_db=conn,
                            )

                            if set_created:
                                set_log_created += 1
                            else:
                                updated = False
                                for field in ("weight", "reps", "is_completed"):
                                    expected = set_item[field]
                                    if getattr(set_log, field) != expected:
                                        setattr(set_log, field, expected)
                                        updated = True
                                if updated:
                                    await set_log.save(using_db=conn)

                        cardio_item = log_item.get("cardio")
                        if cardio_item:
                            cardio_log, cardio_created = await CardioLog.get_or_create(
                                workout_log=workout_log,
                                defaults=cardio_item,
                                using_db=conn,
                            )

                            if cardio_created:
                                cardio_log_created += 1
                            else:
                                updated = False
                                for field, expected in cardio_item.items():
                                    if getattr(cardio_log, field) != expected:
                                        setattr(cardio_log, field, expected)
                                        updated = True
                                if updated:
                                    await cardio_log.save(using_db=conn)

        print(
            "[dummy-session] seeding completed "
            f"(sessions_created={session_created}, workout_logs_created={workout_log_created}, "
            f"set_logs_created={set_log_created}, cardio_logs_created={cardio_log_created})"
        )
    except Exception as error:
        print(f"[dummy-session] seeding failed: {error}")
