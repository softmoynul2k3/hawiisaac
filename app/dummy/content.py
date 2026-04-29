from tortoise.transactions import in_transaction
from app.config import settings

from applications.content.models import (
    Content,
    ContentBookmark,
    ContentReaction,
    ContentShare,
    ContentView,
)
from applications.equipments.models import Workout, WorkoutType
from applications.user.models import User


BASE_URL = settings.BASE_URL

CONTENT_DATA = [
    {
        "title": "Beginner Strength Training Basics",
        "workout_names": [
            "Dumbbell Shoulder Press",
            "Barbell Deadlift",
            "Incline Dumbbell Chest Fly",
            "Cable Tricep Pushdown",
            "Leg Press Machine",
            "Barbell Back Squat",
            "Seated Cable Row",
            "Plank Hold",
            "Bosu Ball Single-Leg Squat",
            "Foam Roll Recovery",
        ],
        "summary": "A practical intro to getting started with strength work without overcomplicating your first month.",
        "body": (
            "Start with full-body sessions two or three times each week. Focus on a few repeatable movements, "
            "track your loads, and give yourself enough recovery time to improve steadily."
        ),
        "image": f"{BASE_URL}/assets/banner1.png",
        "video": f"{BASE_URL}/assets/banner1.mp4",
        "is_active": True,
    },
    {
        "title": "Mobility Reset for Desk Workers",
        "workout_names": [
            "Foam Roll Recovery",
            "Bosu Ball Single-Leg Squat",
            "Plank Hold",
            "Incline Dumbbell Chest Fly",
            "Seated Cable Row",
            "Cable Tricep Pushdown",
        ],
        "summary": "A short mobility routine for hips, shoulders, and upper back that fits between meetings.",
        "body": (
            "This sequence mixes breathing, thoracic rotation, hip openers, and gentle hamstring work. "
            "It is designed for consistency more than intensity."
        ),
        "image": f"{BASE_URL}/assets/banner2.jpg",
        "video": f"{BASE_URL}/assets/banner2.mp4",
        "is_active": True,
    },
    {
        "title": "Zone 2 Cardio Explained",
        "workout_names": [
            "Treadmill Sprint Intervals",
            "Rowing Machine Endurance",
            "Stationary Bike Steady State",
            "Stair Climber Intervals",
            "Jump Rope HIIT",
            "Kettlebell Swing",
            "Battle Rope Waves",
            "Box Jumps",
        ],
        "summary": "Why easy cardio matters, how to pace it, and where it fits beside lifting days.",
        "body": (
            "Zone 2 training helps build aerobic capacity and recovery without draining the nervous system. "
            "Use conversational effort and keep the sessions long enough to be meaningful."
        ),
        "image": f"{BASE_URL}/assets/banner3.jpg",
        "video": f"{BASE_URL}/assets/banner3.mp4",
        "is_active": True,
    },
    {
        "title": "HIIT for Fat Loss",
        "workout_names": [
            "Treadmill Sprint Intervals",
            "Jump Rope HIIT",
            "Battle Rope Waves",
            "Box Jumps",
            "Kettlebell Swing",
            "Stair Climber Intervals",
        ],
        "summary": "High-intensity interval training protocols designed to maximise calorie burn in minimal time.",
        "body": (
            "HIIT sessions alternate between short bursts of near-maximal effort and brief recovery periods. "
            "Keep total work volume moderate and prioritise form to reduce injury risk."
        ),
        "image": f"{BASE_URL}/assets/banner4.png",
        "video": f"{BASE_URL}/assets/banner4.mp4",
        "is_active": True,
    },
    {
        "title": "Full Body Power Circuit",
        "workout_names": [
            "Barbell Deadlift",
            "Barbell Back Squat",
            "Kettlebell Swing",
            "Box Jumps",
            "Battle Rope Waves",
            "Treadmill Sprint Intervals",
            "Plank Hold",
        ],
        "summary": "A mixed-type circuit combining compound strength lifts with explosive cardio bursts.",
        "body": (
            "Alternate between a strength movement and a cardio burst with minimal rest between pairs. "
            "This approach builds work capacity and muscular endurance simultaneously."
        ),
        "image": f"{BASE_URL}/assets/banner1.png",
        "video": f"{BASE_URL}/assets/banner1.mp4",
        "is_active": True,
    },
]


INTERACTION_SEED = [
    {
        "email": "user1@gmail.com",
        "bookmarks": ["Beginner Strength Training Basics", "Zone 2 Cardio Explained"],
        "shares": [
            ("Beginner Strength Training Basics", "facebook"),
            ("Mobility Reset for Desk Workers", "whatsapp"),
        ],
        "reactions": [
            ("Beginner Strength Training Basics", "like"),
            ("Mobility Reset for Desk Workers", "love"),
        ],
        "views": [
            "Beginner Strength Training Basics",
            "Beginner Strength Training Basics",
            "Mobility Reset for Desk Workers",
        ],
    },
    {
        "email": "user2@gmail.com",
        "bookmarks": ["Mobility Reset for Desk Workers", "HIIT for Fat Loss"],
        "shares": [
            ("Zone 2 Cardio Explained", "twitter"),
            ("HIIT for Fat Loss", "whatsapp"),
        ],
        "reactions": [
            ("Zone 2 Cardio Explained", "like"),
            ("Beginner Strength Training Basics", "clap"),
            ("HIIT for Fat Loss", "love"),
        ],
        "views": [
            "Zone 2 Cardio Explained",
            "Zone 2 Cardio Explained",
            "Zone 2 Cardio Explained",
            "Beginner Strength Training Basics",
            "HIIT for Fat Loss",
            "HIIT for Fat Loss",
        ],
    },
    {
        "email": "user3@gmail.com",
        "bookmarks": ["Full Body Power Circuit", "HIIT for Fat Loss"],
        "shares": [
            ("Full Body Power Circuit", "facebook"),
        ],
        "reactions": [
            ("Full Body Power Circuit", "love"),
            ("HIIT for Fat Loss", "like"),
        ],
        "views": [
            "Full Body Power Circuit",
            "Full Body Power Circuit",
            "Full Body Power Circuit",
            "HIIT for Fat Loss",
        ],
    },
]


async def create_test_content():
    content_created = 0
    content_updated = 0
    bookmark_created = 0
    share_created = 0
    reaction_created = 0
    reaction_updated = 0
    view_created = 0

    try:
        async with in_transaction() as conn:
            workout_names = [
                workout_name
                for item in CONTENT_DATA
                for workout_name in item.get("workout_names", [])
            ]
            workouts = await Workout.filter(
                name__in=workout_names,
                workout_type=WorkoutType.CARDIO,  # ← only cardio workouts
            ).using_db(conn)
            workouts_by_name = {workout.name: workout for workout in workouts}

            contents_by_title = {}
            for item in CONTENT_DATA:
                ordered_workout_names = item.get("workout_names", [])
                ordered_workouts = []
                missing_workouts = []
                for workout_name in ordered_workout_names:
                    workout = workouts_by_name.get(workout_name)
                    if workout:
                        ordered_workouts.append(workout)
                    else:
                        missing_workouts.append(workout_name)
                if missing_workouts:
                    print(f"[dummy-content] skipped missing workout link(s): {', '.join(missing_workouts)}")

                content, created = await Content.get_or_create(
                    title=item["title"],
                    defaults={
                        "summary": item["summary"],
                        "body": item["body"],
                        "image": item["image"],
                        "video": item["video"],
                        "is_active": item["is_active"],
                    },
                    using_db=conn,
                )

                if created:
                    content_created += 1
                else:
                    updated = False
                    for field in ("summary", "body", "image", "video", "is_active"):
                        if getattr(content, field) != item[field]:
                            setattr(content, field, item[field])
                            updated = True
                    if updated:
                        await content.save(using_db=conn)
                        content_updated += 1

                current_workout_ids = sorted([workout.id for workout in await content.workouts.all().using_db(conn)])
                expected_workout_ids = [workout.id for workout in ordered_workouts]
                if current_workout_ids != sorted(expected_workout_ids):
                    await content.workouts.clear(using_db=conn)
                    if ordered_workouts:
                        await content.workouts.add(*ordered_workouts, using_db=conn)

                contents_by_title[item["title"]] = content

            users = await User.filter(email__in=[item["email"] for item in INTERACTION_SEED]).using_db(conn)
            users_by_email = {user.email: user for user in users}

            for item in INTERACTION_SEED:
                user = users_by_email.get(item["email"])
                if not user:
                    print(f"[dummy-content] skipped missing user: {item['email']}")
                    continue

                for title in item.get("bookmarks", []):
                    content = contents_by_title.get(title)
                    if not content:
                        continue
                    _, created = await ContentBookmark.get_or_create(user=user, content=content, using_db=conn)
                    if created:
                        bookmark_created += 1

                for title, platform in item.get("shares", []):
                    content = contents_by_title.get(title)
                    if not content:
                        continue
                    exists = await ContentShare.filter(user=user, content=content, platform=platform).using_db(conn).exists()
                    if not exists:
                        await ContentShare.create(user=user, content=content, platform=platform, using_db=conn)
                        share_created += 1

                for title, reaction_type in item.get("reactions", []):
                    content = contents_by_title.get(title)
                    if not content:
                        continue
                    reaction, created = await ContentReaction.get_or_create(
                        user=user,
                        content=content,
                        defaults={"reaction_type": reaction_type},
                        using_db=conn,
                    )
                    if created:
                        reaction_created += 1
                    elif reaction.reaction_type != reaction_type:
                        reaction.reaction_type = reaction_type
                        await reaction.save(using_db=conn)
                        reaction_updated += 1

                existing_view_counts = {}
                rows = await ContentView.filter(
                    user=user,
                    content_id__in=[content.id for content in contents_by_title.values()],
                ).using_db(conn)
                for row in rows:
                    existing_view_counts[row.content_id] = existing_view_counts.get(row.content_id, 0) + 1

                requested_view_counts = {}
                for title in item.get("views", []):
                    content = contents_by_title.get(title)
                    if not content:
                        continue
                    requested_view_counts[content.id] = requested_view_counts.get(content.id, 0) + 1

                for content_id, needed_count in requested_view_counts.items():
                    existing_count = existing_view_counts.get(content_id, 0)
                    for _ in range(max(needed_count - existing_count, 0)):
                        await ContentView.create(user=user, content_id=content_id, using_db=conn)
                        view_created += 1

        print(
            "[dummy-content] seeding completed "
            f"(content_created={content_created}, content_updated={content_updated}, "
            f"bookmarks_created={bookmark_created}, shares_created={share_created}, "
            f"reactions_created={reaction_created}, reactions_updated={reaction_updated}, "
            f"views_created={view_created})"
        )
    except Exception as error:
        print(f"[dummy-content] seeding failed: {error}")