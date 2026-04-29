from tortoise.transactions import in_transaction

from applications.equipments.models import (
    Category,
    Equipment,
    MuscleGroups,
    Workout,
    WorkoutType,
)

# ---------------------------
# MEDIA DATA
# ---------------------------
PEXELS_IMAGE_URLS = [
    "https://images.pexels.com/photos/6389513/pexels-photo-6389513.jpeg",
    "https://images.pexels.com/photos/6388466/pexels-photo-6388466.jpeg",
    "https://images.pexels.com/photos/6796964/pexels-photo-6796964.jpeg",
    "https://images.pexels.com/photos/6389516/pexels-photo-6389516.jpeg",
]

PEXELS_BANNER_URLS = [
    "https://images.pexels.com/photos/6389516/pexels-photo-6389516.jpeg",
    "https://images.pexels.com/photos/6796964/pexels-photo-6796964.jpeg",
    "https://images.pexels.com/photos/6389513/pexels-photo-6389513.jpeg",
]

PEXELS_VIDEO_URLS = [
    "https://www.pexels.com/video/dumbbell-weights-20621391/",
    "https://www.pexels.com/video/video-of-gym-equipment-8027708/",
    "https://www.pexels.com/video/a-person-using-a-treadmill-6892539/",
]

# ---------------------------
# CATEGORY DATA
# ---------------------------
CATEGORY_DATA = [
    ("Strength", "Resistance training and hypertrophy focus."),
    ("Cardio", "Endurance and heart health workouts."),
    ("Mobility", "Flexibility and recovery movement."),
    ("Functional Training", "Real-world movement patterns."),
    ("Core", "Core stability and abdominal strength."),
    ("Upper Body", "Chest, back, arms, shoulders."),
    ("Lower Body", "Leg and glute development."),
    ("Rehabilitation", "Low-impact recovery training."),
    ("Studio", "Group class style equipment."),
    ("Athletic Performance", "Speed, power, agility training."),
]

# ---------------------------
# EQUIPMENT GROUP DATA
# ---------------------------
EQUIPMENT_GROUP_DATA = [
    ("Free Weights", "Classic strength tools with unrestricted movement."),
    ("Machine Based", "Guided-path equipment for controlled training."),
    ("Cable Systems", "Adjustable pulley resistance systems."),
    ("Benches & Racks", "Support structures for lifting."),
    ("Conditioning Tools", "Cardio and metabolic training tools."),
    ("Bodyweight Support", "Assisted bodyweight training stations."),
    ("Recovery Tools", "Mobility and recovery accessories."),
    ("Balance Training", "Stability and coordination tools."),
    ("Studio Accessories", "Class-based training equipment."),
    ("Performance Gear", "Explosive athletic training tools."),
]

# ---------------------------
# MUSCLE GROUP DATA
# ---------------------------
MUSCLE_GROUP_DATA = [
    ("Chest", "Pectoral muscles for pushing."),
    ("Back", "Pulling and posture muscles."),
    ("Shoulders", "Deltoid stabilization and pressing."),
    ("Biceps", "Arm flexion muscles."),
    ("Triceps", "Arm extension muscles."),
    ("Forearms", "Grip and wrist control."),
    ("Core", "Core stability muscles."),
    ("Glutes", "Hip extension power muscles."),
    ("Quadriceps", "Front thigh muscles."),
    ("Hamstrings", "Rear thigh muscles."),
    ("Calves", "Lower leg propulsion muscles."),
    ("Full Body", "Multi-muscle compound movements."),
]

# ---------------------------
# WORKOUT DATA
# NON_CARDIO → sets/reps/rest filled, cardio fields None
# CARDIO     → time/distance/speed/incline/duration filled, sets/reps/rest = ""
# ---------------------------
WORKOUT_DATA = [
    # ── NON-CARDIO ──────────────────────────────────────────────
    {
        "name": "Dumbbell Shoulder Press",
        "category": "Strength",
        "equipment": "Free Weights",
        "muscles": ["Shoulders", "Triceps"],
        "description": "Overhead pressing movement for shoulder strength and mass.",
        "tags": "strength,shoulders,dumbbells",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 4.5,
        "uses": ["strength", "hypertrophy"],
        "sets": "4", "reps": "8-12", "rest": "60 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Barbell Deadlift",
        "category": "Strength",
        "equipment": "Free Weights",
        "muscles": ["Back", "Glutes", "Hamstrings"],
        "description": "Full posterior chain compound lift for raw strength.",
        "tags": "powerlifting,back,compound",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 6.0,
        "uses": ["powerlifting", "strength"],
        "sets": "5", "reps": "5", "rest": "120 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Incline Dumbbell Chest Fly",
        "category": "Upper Body",
        "equipment": "Free Weights",
        "muscles": ["Chest", "Shoulders"],
        "description": "Isolation movement targeting upper pectoral fibers.",
        "tags": "chest,isolation,dumbbells",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 3.8,
        "uses": ["hypertrophy", "isolation"],
        "sets": "3", "reps": "12-15", "rest": "45 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Cable Tricep Pushdown",
        "category": "Upper Body",
        "equipment": "Cable Systems",
        "muscles": ["Triceps", "Forearms"],
        "description": "Cable-based arm extension for tricep definition.",
        "tags": "triceps,cable,arms",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 3.5,
        "uses": ["hypertrophy", "toning"],
        "sets": "4", "reps": "10-15", "rest": "45 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Leg Press Machine",
        "category": "Lower Body",
        "equipment": "Machine Based",
        "muscles": ["Quadriceps", "Glutes", "Hamstrings"],
        "description": "Machine-guided quad and glute pressing movement.",
        "tags": "legs,quads,machine",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 5.0,
        "uses": ["strength", "hypertrophy"],
        "sets": "4", "reps": "10-12", "rest": "90 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Barbell Back Squat",
        "category": "Lower Body",
        "equipment": "Benches & Racks",
        "muscles": ["Quadriceps", "Glutes", "Core"],
        "description": "King of lower body exercises for overall leg development.",
        "tags": "squat,compound,legs",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 5.5,
        "uses": ["powerlifting", "strength"],
        "sets": "5", "reps": "5-8", "rest": "120 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Plank Hold",
        "category": "Core",
        "equipment": "Bodyweight Support",
        "muscles": ["Core"],
        "description": "Isometric core stabilization hold.",
        "tags": "core,isometric,stability",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 3.0,
        "uses": ["stability", "endurance"],
        "sets": "3", "reps": "60 sec", "rest": "30 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Seated Cable Row",
        "category": "Upper Body",
        "equipment": "Cable Systems",
        "muscles": ["Back", "Biceps"],
        "description": "Horizontal pull for mid-back thickness and bicep engagement.",
        "tags": "back,cable,pulling",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 4.0,
        "uses": ["hypertrophy", "strength"],
        "sets": "4", "reps": "10-12", "rest": "60 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Foam Roll Recovery",
        "category": "Rehabilitation",
        "equipment": "Recovery Tools",
        "muscles": ["Full Body"],
        "description": "Self-myofascial release for muscle recovery and mobility.",
        "tags": "recovery,mobility,foam roll",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 2.5,
        "uses": ["recovery", "mobility"],
        "sets": "1", "reps": "10 min", "rest": "0 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },
    {
        "name": "Bosu Ball Single-Leg Squat",
        "category": "Rehabilitation",
        "equipment": "Balance Training",
        "muscles": ["Quadriceps", "Glutes", "Core"],
        "description": "Unilateral balance and stability squat variation.",
        "tags": "balance,rehab,unilateral",
        "workout_type": WorkoutType.NON_CARDIO,
        "met_value": 4.2,
        "uses": ["rehabilitation", "balance"],
        "sets": "3", "reps": "10 each side", "rest": "45 sec",
        "time": None, "distance": None, "speed": None, "incline": None, "duration": None,
    },

    # ── CARDIO ───────────────────────────────────────────────────
    {
        "name": "Treadmill Sprint Intervals",
        "category": "Cardio",
        "equipment": "Conditioning Tools",
        "muscles": ["Full Body"],
        "description": "High-intensity interval running for fat loss and conditioning.",
        "tags": "hiit,running,fat loss",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 12.0,
        "uses": ["hiit", "fat loss"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:20:00", "distance": 4, "speed": 14, "incline": 1, "duration": "00:20:00",
    },
    {
        "name": "Rowing Machine Endurance",
        "category": "Cardio",
        "equipment": "Conditioning Tools",
        "muscles": ["Back", "Core", "Full Body"],
        "description": "Full-body endurance rowing session for aerobic base building.",
        "tags": "rowing,endurance,cardio",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 7.0,
        "uses": ["endurance", "cardio"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:15:00", "distance": 2, "speed": 8, "incline": 0, "duration": "00:15:00",
    },
    {
        "name": "Kettlebell Swing",
        "category": "Functional Training",
        "equipment": "Performance Gear",
        "muscles": ["Glutes", "Core", "Hamstrings"],
        "description": "Explosive hip hinge movement with high metabolic demand.",
        "tags": "kettlebell,explosive,functional",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 9.8,
        "uses": ["functional", "explosive"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:12:00", "distance": 0, "speed": 0, "incline": 0, "duration": "00:12:00",
    },
    {
        "name": "Jump Rope HIIT",
        "category": "Cardio",
        "equipment": "Studio Accessories",
        "muscles": ["Calves", "Full Body"],
        "description": "High-cadence skipping intervals for cardiovascular fitness.",
        "tags": "jump rope,hiit,cardio",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 11.0,
        "uses": ["hiit", "conditioning"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:15:00", "distance": 0, "speed": 0, "incline": 0, "duration": "00:15:00",
    },
    {
        "name": "Stationary Bike Steady State",
        "category": "Cardio",
        "equipment": "Conditioning Tools",
        "muscles": ["Quadriceps", "Hamstrings", "Calves"],
        "description": "Moderate-intensity cycling session for aerobic endurance.",
        "tags": "cycling,steady state,low impact",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 6.5,
        "uses": ["endurance", "fat loss"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:40:00", "distance": 18, "speed": 27, "incline": 0, "duration": "00:40:00",
    },
    {
        "name": "Battle Rope Waves",
        "category": "Athletic Performance",
        "equipment": "Performance Gear",
        "muscles": ["Shoulders", "Core", "Full Body"],
        "description": "Upper-body dominant cardio using heavy battle ropes.",
        "tags": "battle rope,hiit,athletic",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 10.5,
        "uses": ["hiit", "conditioning"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:12:30", "distance": 0, "speed": 0, "incline": 0, "duration": "00:12:30",
    },
    {
        "name": "Stair Climber Intervals",
        "category": "Cardio",
        "equipment": "Conditioning Tools",
        "muscles": ["Glutes", "Quadriceps", "Calves"],
        "description": "Step-climbing intervals for lower body cardio and glute activation.",
        "tags": "stairmaster,intervals,glutes",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 9.0,
        "uses": ["cardio", "glutes"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:15:00", "distance": 0, "speed": 0, "incline": 10, "duration": "00:15:00",
    },
    {
        "name": "Box Jumps",
        "category": "Athletic Performance",
        "equipment": "Performance Gear",
        "muscles": ["Quadriceps", "Glutes", "Calves"],
        "description": "Plyometric explosive jump for power and cardio output.",
        "tags": "plyometric,explosive,power",
        "workout_type": WorkoutType.CARDIO,
        "met_value": 8.5,
        "uses": ["explosive", "athletic"],
        "sets": "", "reps": "", "rest": "",
        "time": "00:10:00", "distance": 0, "speed": 0, "incline": 0, "duration": "00:10:00",
    },
]


# ---------------------------
# SEED FUNCTION
# ---------------------------
async def create_test_equipments():
    stats = {
        "categories": 0,
        "equipment": 0,
        "muscles": 0,
        "workouts_created": 0,
        "workouts_updated": 0,
    }

    try:
        async with in_transaction():

            # ---------------- CATEGORY ----------------
            categories = {}
            for name, desc in CATEGORY_DATA:
                obj, created = await Category.get_or_create(
                    name=name,
                    defaults={"description": desc},
                )
                if created:
                    stats["categories"] += 1
                categories[name] = obj

            # ---------------- EQUIPMENT ----------------
            equipments = {}
            for i, (name, desc) in enumerate(EQUIPMENT_GROUP_DATA):
                obj, created = await Equipment.get_or_create(
                    name=name,
                    defaults={
                        "description": desc,
                        "image": PEXELS_IMAGE_URLS[i % len(PEXELS_IMAGE_URLS)],
                        "category": categories["Strength"],
                    },
                )
                if created:
                    stats["equipment"] += 1
                equipments[name] = obj

            # ---------------- MUSCLES ----------------
            muscles = {}
            for name, desc in MUSCLE_GROUP_DATA:
                obj, created = await MuscleGroups.get_or_create(
                    name=name,
                    defaults={"description": desc},
                )
                if created:
                    stats["muscles"] += 1
                muscles[name] = obj

            # ---------------- WORKOUTS ----------------
            for i, item in enumerate(WORKOUT_DATA):

                category = categories[item["category"]]
                equipment = equipments.get(item["equipment"])
                muscle_objs = [muscles[m] for m in item["muscles"] if m in muscles]

                defaults = {
                    "category": category,
                    "equipment": equipment,
                    "description": item["description"],
                    "tags": item.get("tags", ""),
                    "workout_type": item["workout_type"],
                    "met_value": item["met_value"],
                    "uses": item["uses"],
                    "banner": PEXELS_BANNER_URLS[i % len(PEXELS_BANNER_URLS)],
                    "video": PEXELS_VIDEO_URLS[i % len(PEXELS_VIDEO_URLS)],
                    # always present — empty string for cardio, None fields for non-cardio
                    "sets": item["sets"],
                    "reps": item["reps"],
                    "rest": item["rest"],
                    "time": item["time"],
                    "distance": item["distance"],
                    "speed": item["speed"],
                    "incline": item["incline"],
                    "duration": item["duration"],
                }

                workout, created = await Workout.get_or_create(
                    name=item["name"],
                    defaults=defaults,
                )

                if created:
                    stats["workouts_created"] += 1
                else:
                    updated = False
                    for k, v in defaults.items():
                        if getattr(workout, k) != v:
                            setattr(workout, k, v)
                            updated = True
                    if updated:
                        await workout.save()
                        stats["workouts_updated"] += 1

                await workout.muscle_groups.clear()
                if muscle_objs:
                    await workout.muscle_groups.add(*muscle_objs)

        print("[seed completed]", stats)

    except Exception as e:
        print("[seed error]", str(e))