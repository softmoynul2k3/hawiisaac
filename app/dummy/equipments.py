from tortoise.transactions import in_transaction

from applications.equipments.models import Category, Equipment, MuscleGroups, Workout

PEXELS_IMAGE_URLS = [
    "https://images.pexels.com/photos/6389513/pexels-photo-6389513.jpeg?cs=srgb&dl=pexels-tima-miroshnichenko-6389513.jpg&fm=jpg",
    "https://images.pexels.com/photos/6388466/pexels-photo-6388466.jpeg?cs=srgb&dl=pexels-tima-miroshnichenko-6388466.jpg&fm=jpg",
    "https://images.pexels.com/photos/6796964/pexels-photo-6796964.jpeg?cs=srgb&dl=pexels-dimkidama-6796964.jpg&fm=jpg",
    "https://images.pexels.com/photos/6389516/pexels-photo-6389516.jpeg?cs=srgb&dl=pexels-tima-miroshnichenko-6389516.jpg&fm=jpg",
]

PEXELS_BANNER_URLS = [
    "https://images.pexels.com/photos/6389516/pexels-photo-6389516.jpeg?cs=srgb&dl=pexels-tima-miroshnichenko-6389516.jpg&fm=jpg",
    "https://images.pexels.com/photos/6796964/pexels-photo-6796964.jpeg?cs=srgb&dl=pexels-dimkidama-6796964.jpg&fm=jpg",
    "https://images.pexels.com/photos/6389513/pexels-photo-6389513.jpeg?cs=srgb&dl=pexels-tima-miroshnichenko-6389513.jpg&fm=jpg",
    "https://images.pexels.com/videos/7986045/pexels-photo-7986045.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=500",
]

PEXELS_VIDEO_URLS = [
    "https://www.pexels.com/video/dumbbell-weights-20621391/",
    "https://www.pexels.com/video/video-of-gym-equipment-8027708/",
    "https://www.pexels.com/video/a-person-using-a-treadmill-6892539/",
    "https://www.pexels.com/video/running-on-treadmill-992697/",
    "https://www.pexels.com/video/a-man-using-a-treadmill-5320011/",
    "https://www.pexels.com/video/a-man-exercising-using-a-medicine-ball-4745732/",
]


CATEGORY_DATA = [
    {
        "name": "Strength",
        "description": "Workout focused on resistance training and progressive overload.",
    },
    {
        "name": "Cardio",
        "description": "Machines and tools designed to improve endurance and heart health.",
    },
    {
        "name": "Mobility",
        "description": "Supportive tools for stretching, warm-up, and recovery work.",
    },
    {
        "name": "Functional Training",
        "description": "Versatile equipment for compound movement and total-body routines.",
    },
    {
        "name": "Core",
        "description": "Workout often used to strengthen the trunk and improve stability.",
    },
    {
        "name": "Upper Body",
        "description": "Focused tools for chest, shoulders, arms, and back development.",
    },
    {
        "name": "Lower Body",
        "description": "Workout dedicated to quads, hamstrings, glutes, and calves.",
    },
    {
        "name": "Rehabilitation",
        "description": "Low-impact equipment suitable for controlled movement and recovery.",
    },
    {
        "name": "Studio",
        "description": "Compact accessories commonly used in classes and home workouts.",
    },
    {
        "name": "Athletic Performance",
        "description": "Tools used for power, speed, coordination, and sports training.",
    },
]

EQUIPMENT_GROUP_DATA = [
    {"name": "Free Weights", "description": "Classic strength tools with unrestricted movement patterns."},
    {"name": "Machine Based", "description": "Guided-path equipment for controlled and isolated training."},
    {"name": "Cable Systems", "description": "Adjustable pulley equipment for varied resistance angles."},
    {"name": "Benches & Racks", "description": "Support structures for pressing, racking, and setup work."},
    {"name": "Conditioning Tools", "description": "Workout for circuits, intervals, and metabolic training."},
    {"name": "Bodyweight Support", "description": "Stations that assist or challenge bodyweight exercises."},
    {"name": "Recovery Tools", "description": "Accessories for cooldowns, flexibility, and muscle care."},
    {"name": "Balance Training", "description": "Tools that improve stability, coordination, and control."},
    {"name": "Studio Accessories", "description": "Portable training gear used in classes and small spaces."},
    {"name": "Performance Gear", "description": "Explosive training tools for athletes and advanced users."},
]

MUSCLE_GROUP_DATA = [
    {"name": "Chest", "description": "Pectoral muscles used in pressing and adduction movements."},
    {"name": "Back", "description": "Upper and mid-back muscles involved in pulling and posture."},
    {"name": "Shoulders", "description": "Deltoid-focused work for pressing, raising, and stabilization."},
    {"name": "Biceps", "description": "Front upper-arm muscles active in elbow flexion and pulling."},
    {"name": "Triceps", "description": "Rear upper-arm muscles used in pressing and elbow extension."},
    {"name": "Forearms", "description": "Grip and wrist muscles important for carries and control."},
    {"name": "Core", "description": "Abdominal and trunk muscles for stability, bracing, and rotation."},
    {"name": "Glutes", "description": "Hip extension muscles essential for power and lower-body strength."},
    {"name": "Quadriceps", "description": "Front thigh muscles emphasized in squats and knee extension."},
    {"name": "Hamstrings", "description": "Rear thigh muscles for hinging, sprinting, and knee flexion."},
    {"name": "Calves", "description": "Lower-leg muscles supporting ankle drive and stability."},
    {"name": "Full Body", "description": "Compound patterns that challenge multiple major muscle groups."},
]

EQUIPMENT_DATA = [
    ("Strength", "Free Weights", ["Shoulders", "Biceps", "Triceps", "Quadriceps", "Glutes"], "Adjustable Dumbbells", "Versatile dumbbell pair for presses, rows, curls, and lunges.", "4", "8-12", "60 sec", ["upper-body strength", "lower-body strength", "home workouts"]),
    ("Strength", "Free Weights", ["Back", "Glutes", "Hamstrings", "Quadriceps", "Full Body"], "Olympic Barbell", "Standard barbell for compound lifts and progressive loading.", "5", "5", "120 sec", ["squats", "deadlifts", "bench press"]),
    ("Strength", "Machine Based", ["Quadriceps", "Glutes", "Hamstrings"], "Leg Press Machine", "Lower-body machine targeting quads and glutes with guided support.", "4", "10-15", "75 sec", ["leg strength", "glute training"]),
    ("Strength", "Machine Based", ["Chest", "Shoulders", "Triceps"], "Chest Press Machine", "Seated pushing machine for chest, shoulders, and triceps.", "4", "8-12", "60 sec", ["chest training", "upper-body strength"]),
    ("Strength", "Cable Systems", ["Chest", "Back", "Shoulders", "Core"], "Dual Cable Cross", "Cable unit for flyes, rows, chops, and functional patterns.", "3", "12-15", "45 sec", ["functional training", "isolation work"]),
    ("Cardio", "Conditioning Tools", ["Full Body", "Quadriceps", "Glutes", "Calves"], "Treadmill", "Indoor running and walking machine with adjustable incline.", "1", "20 min", "0 sec", ["running", "walking", "fat loss"]),
    ("Cardio", "Conditioning Tools", ["Full Body", "Quadriceps", "Glutes", "Core"], "Air Bike", "Fan-resistance bike for high-intensity intervals and conditioning.", "8", "30 sec", "30 sec", ["HIIT", "conditioning"]),
    ("Cardio", "Conditioning Tools", ["Back", "Core", "Quadriceps", "Hamstrings"], "Rowing Machine", "Full-body cardio equipment with low joint impact.", "5", "500 m", "60 sec", ["endurance", "low-impact cardio"]),
    ("Cardio", "Conditioning Tools", ["Quadriceps", "Glutes", "Calves"], "Elliptical Trainer", "Smooth cardio machine for low-impact steady-state sessions.", "1", "25 min", "0 sec", ["steady-state cardio", "joint-friendly training"]),
    ("Cardio", "Performance Gear", ["Quadriceps", "Glutes", "Calves", "Core"], "Sled Push", "Weighted sled for acceleration, leg drive, and work capacity.", "6", "20 m", "60 sec", ["athletic conditioning", "power"]),
    ("Mobility", "Recovery Tools", ["Full Body"], "Foam Roller", "Self-myofascial release tool for warm-ups and recovery.", "3", "60 sec", "20 sec", ["recovery", "mobility"]),
    ("Mobility", "Recovery Tools", ["Full Body"], "Massage Ball", "Small release tool for targeted trigger point work.", "3", "45 sec", "15 sec", ["recovery", "foot mobility"]),
    ("Mobility", "Studio Accessories", ["Hamstrings", "Glutes", "Back"], "Stretch Strap", "Helps deepen stretches and improve range of motion.", "3", "30 sec", "15 sec", ["stretching", "mobility"]),
    ("Mobility", "Balance Training", ["Full Body"], "Yoga Block", "Supportive prop for mobility drills and assisted poses.", "2", "60 sec", "15 sec", ["flexibility", "pose support"]),
    ("Mobility", "Bodyweight Support", ["Back", "Biceps"], "Pull-Up Assist Band", "Elastic band that supports pull-ups and mobility drills.", "3", "8-10", "45 sec", ["assisted pull-ups", "activation"]),
    ("Functional Training", "Conditioning Tools", ["Full Body", "Core", "Glutes", "Shoulders"], "Kettlebell", "Offset load tool for swings, carries, and presses.", "4", "12-15", "45 sec", ["functional strength", "conditioning"]),
    ("Functional Training", "Cable Systems", ["Shoulders", "Core", "Forearms"], "Battle Rope", "Rope training tool for intervals and total-body endurance.", "10", "20 sec", "20 sec", ["conditioning", "grip endurance"]),
    ("Functional Training", "Performance Gear", ["Quadriceps", "Glutes", "Calves"], "Plyo Box", "Platform for jumps, step-ups, and explosive lower-body work.", "5", "6-8", "60 sec", ["jump training", "power"]),
    ("Functional Training", "Studio Accessories", ["Shoulders", "Glutes", "Core"], "Resistance Band Set", "Portable bands for warm-up, strengthening, and rehab.", "3", "15-20", "30 sec", ["activation", "travel workouts"]),
    ("Functional Training", "Balance Training", ["Back", "Chest", "Core", "Shoulders"], "Suspension Trainer", "Strap system for bodyweight rows, presses, and core work.", "4", "10-15", "45 sec", ["bodyweight training", "core stability"]),
    ("Core", "Studio Accessories", ["Core", "Shoulders"], "Ab Wheel", "Rolling tool that challenges anti-extension core strength.", "4", "8-12", "45 sec", ["core strength", "anti-extension"]),
    ("Core", "Machine Based", ["Core", "Back", "Glutes"], "Roman Chair", "Bench station for back extensions and trunk control work.", "3", "12-15", "45 sec", ["posterior chain", "core endurance"]),
    ("Core", "Bodyweight Support", ["Core", "Chest", "Triceps"], "Dip Station", "Station for leg raises, dips, and bodyweight support drills.", "4", "10-15", "60 sec", ["leg raises", "triceps", "core"]),
    ("Core", "Balance Training", ["Core", "Back"], "Stability Ball", "Inflatable ball for trunk control and mobility drills.", "3", "12-20", "30 sec", ["core stability", "balance"]),
    ("Core", "Cable Systems", ["Core"], "Cable Crunch Attachment", "Rope attachment setup for weighted abdominal work.", "4", "12-15", "45 sec", ["abdominal training", "cable work"]),
    ("Upper Body", "Machine Based", ["Back", "Biceps"], "Lat Pulldown Machine", "Guided vertical pull for the lats and upper back.", "4", "8-12", "60 sec", ["back training", "lat development"]),
    ("Upper Body", "Machine Based", ["Back", "Biceps", "Shoulders"], "Seated Row Machine", "Horizontal pull machine for rhomboids, traps, and lats.", "4", "10-12", "60 sec", ["back thickness", "posture"]),
    ("Upper Body", "Benches & Racks", ["Chest", "Shoulders", "Triceps"], "Adjustable Bench", "Bench with incline settings for pressing and support work.", "3", "10-12", "45 sec", ["bench press", "incline press"]),
    ("Upper Body", "Free Weights", ["Biceps", "Triceps", "Forearms"], "EZ Curl Bar", "Curved bar suited for curls, skull crushers, and arm work.", "4", "10-15", "45 sec", ["arm training", "joint-friendly curls"]),
    ("Upper Body", "Cable Systems", ["Triceps", "Shoulders"], "Triceps Rope", "Cable attachment for pushdowns, face pulls, and overhead work.", "3", "12-15", "30 sec", ["triceps", "rear delts"]),
    ("Lower Body", "Machine Based", ["Quadriceps", "Glutes", "Hamstrings"], "Hack Squat Machine", "Machine squat variation that emphasizes quads and glutes.", "4", "8-12", "90 sec", ["leg hypertrophy", "quad strength"]),
    ("Lower Body", "Machine Based", ["Hamstrings"], "Leg Curl Machine", "Isolation machine for hamstrings with controlled tempo work.", "4", "10-15", "60 sec", ["hamstrings", "injury prevention"]),
    ("Lower Body", "Machine Based", ["Calves"], "Calf Raise Machine", "Dedicated station for seated or standing calf work.", "5", "12-20", "45 sec", ["calves", "ankle strength"]),
    ("Lower Body", "Benches & Racks", ["Quadriceps", "Glutes", "Hamstrings", "Core"], "Power Rack", "Heavy-duty rack for squats, presses, pulls, and safety pins.", "5", "5-8", "120 sec", ["strength training", "compound lifts"]),
    ("Lower Body", "Performance Gear", ["Quadriceps", "Glutes", "Hamstrings", "Forearms"], "Trap Bar", "Hex bar for deadlifts, carries, and loaded jumps.", "4", "6-8", "90 sec", ["deadlifts", "loaded carries"]),
    ("Rehabilitation", "Recovery Tools", ["Glutes", "Quadriceps"], "Therapy Resistance Loop", "Light loop band for rehab drills and activation.", "3", "15-20", "20 sec", ["rehab", "glute activation"]),
    ("Rehabilitation", "Balance Training", ["Calves", "Quadriceps", "Core"], "Balance Pad", "Soft pad used for ankle, knee, and proprioception work.", "3", "45 sec", "20 sec", ["ankle stability", "rehab balance"]),
    ("Rehabilitation", "Studio Accessories", ["Core"], "Mini Pilates Ball", "Small air-filled ball for controlled rehab and studio exercises.", "3", "12-15", "30 sec", ["rehab core", "posture"]),
    ("Rehabilitation", "Bodyweight Support", ["Chest", "Shoulders", "Triceps", "Core"], "Parallettes", "Low bars used for joint-friendly bodyweight support progressions.", "4", "20 sec", "30 sec", ["calisthenics", "wrist-friendly support"]),
    ("Rehabilitation", "Machine Based", ["Quadriceps", "Glutes"], "Recumbent Bike", "Supportive seated cardio option for recovery-phase training.", "1", "15 min", "0 sec", ["recovery cardio", "low-impact"]),
    ("Studio", "Studio Accessories", ["Full Body"], "Yoga Mat", "Essential mat for floor work, stretching, and mobility practice.", "1", "30 min", "0 sec", ["floor workouts", "stretching"]),
    ("Studio", "Studio Accessories", ["Core", "Glutes"], "Pilates Ring", "Light resistance ring for studio classes and controlled tension.", "3", "12-15", "30 sec", ["pilates", "inner-thigh work"]),
    ("Studio", "Studio Accessories", ["Quadriceps", "Glutes", "Calves"], "Step Platform", "Raised platform for aerobic routines, step-ups, and circuits.", "4", "60 sec", "20 sec", ["step aerobics", "conditioning"]),
    ("Studio", "Balance Training", ["Core", "Quadriceps", "Calves"], "Bosu Ball", "Half-dome trainer for balance challenges and dynamic drills.", "3", "10-12", "45 sec", ["balance", "stability"]),
    ("Studio", "Conditioning Tools", ["Calves", "Shoulders", "Forearms"], "Jump Rope", "Portable cardio tool for rhythm, footwork, and conditioning.", "8", "45 sec", "20 sec", ["conditioning", "coordination"]),
    ("Athletic Performance", "Performance Gear", ["Calves", "Quadriceps", "Core"], "Agility Ladder", "Footwork ladder for speed, timing, and coordination drills.", "6", "30 sec", "20 sec", ["agility", "warm-up"]),
    ("Athletic Performance", "Performance Gear", ["Quadriceps", "Glutes", "Calves"], "Hurdle Set", "Mini hurdles for plyometric and sprint mechanics sessions.", "5", "6-10", "45 sec", ["plyometrics", "speed"]),
    ("Athletic Performance", "Performance Gear", ["Chest", "Shoulders", "Core", "Full Body"], "Medicine Ball", "Weighted ball for throws, slams, and rotational power.", "5", "8-12", "45 sec", ["power", "rotational training"]),
    ("Athletic Performance", "Performance Gear", ["Glutes", "Hamstrings", "Calves"], "Speed Parachute", "Sprint resistance tool for acceleration sessions.", "6", "15 sec", "45 sec", ["sprint training", "resisted runs"]),
    ("Athletic Performance", "Conditioning Tools", ["Full Body", "Core", "Quadriceps", "Glutes"], "Weighted Vest", "Wearable load for walks, carries, and bodyweight progressions.", "4", "10-15", "60 sec", ["loaded carries", "bodyweight progression"]),
]


async def create_test_equipments():
    category_created = 0
    equipment_group_created = 0
    muscle_group_created = 0
    workout_created = 0
    workout_updated = 0

    try:
        async with in_transaction() as conn:
            categories_by_name = {}
            for item in CATEGORY_DATA[:10]:
                category, created = await Category.get_or_create(
                    name=item["name"],
                    defaults={"description": item["description"]},
                    using_db=conn,
                )
                if not created and category.description != item["description"]:
                    category.description = item["description"]
                    await category.save(using_db=conn)
                if created:
                    category_created += 1
                categories_by_name[item["name"]] = category

            equipment_category_by_name = {}
            for category_name, equipment_name, *_ in EQUIPMENT_DATA:
                equipment_category_by_name.setdefault(equipment_name, category_name)

            equipments_by_name = {}
            for equipment_index, item in enumerate(EQUIPMENT_GROUP_DATA[:10]):
                expected_image = PEXELS_IMAGE_URLS[equipment_index % len(PEXELS_IMAGE_URLS)]
                category_name = equipment_category_by_name.get(item["name"], CATEGORY_DATA[0]["name"])
                category = categories_by_name[category_name]
                equipment, created = await Equipment.get_or_create(
                    name=item["name"],
                    defaults={
                        "category": category,
                        "description": item["description"],
                        "image": expected_image,
                    },
                    using_db=conn,
                )
                equipment_changed = False
                if not created and equipment.category_id != category.id:
                    equipment.category = category
                    equipment_changed = True
                if not created and equipment.description != item["description"]:
                    equipment.description = item["description"]
                    equipment_changed = True
                if not created and equipment.image != expected_image:
                    equipment.image = expected_image
                    equipment_changed = True
                if equipment_changed:
                    await equipment.save(using_db=conn)
                if created:
                    equipment_group_created += 1
                equipments_by_name[item["name"]] = equipment

            muscle_groups_by_name = {}
            for item in MUSCLE_GROUP_DATA:
                muscle_group, created = await MuscleGroups.get_or_create(
                    name=item["name"],
                    defaults={"description": item["description"]},
                    using_db=conn,
                )
                if not created and muscle_group.description != item["description"]:
                    muscle_group.description = item["description"]
                    await muscle_group.save(using_db=conn)
                if created:
                    muscle_group_created += 1
                muscle_groups_by_name[item["name"]] = muscle_group

            for index, (
                category_name,
                equipment_name,
                muscle_group_names,
                name,
                description,
                sets,
                reps,
                rest,
                uses,
            ) in enumerate(EQUIPMENT_DATA[:50]):
                category = categories_by_name[category_name]
                equipment = equipments_by_name[equipment_name]
                workout_muscle_groups = [
                    muscle_groups_by_name[muscle_group_name]
                    for muscle_group_name in muscle_group_names
                    if muscle_group_name in muscle_groups_by_name
                ]
                defaults = {
                    "category": category,
                    "equipment": equipment,
                    "description": description,
                    "tags": ", ".join(muscle_group_names),
                    "sets": sets,
                    "reps": reps,
                    "rest": rest,
                    "uses": uses,
                    "banner": PEXELS_BANNER_URLS[index % len(PEXELS_BANNER_URLS)],
                    "video": PEXELS_VIDEO_URLS[index % len(PEXELS_VIDEO_URLS)],
                }

                workout, created = await Workout.get_or_create(
                    name=name,
                    defaults=defaults,
                    using_db=conn,
                )

                if created:
                    workout_created += 1
                    continue

                updated = False
                for field, expected in defaults.items():
                    current = getattr(workout, field)
                    if field in {"category", "equipment"}:
                        current = getattr(workout, f"{field}_id")
                        expected = expected.id if expected else None
                    if current != expected:
                        setattr(workout, field, defaults[field])
                        updated = True

                if updated:
                    await workout.save(using_db=conn)
                    workout_updated += 1

                current_muscle_group_ids = sorted([item.id for item in await workout.muscle_groups.all()])
                expected_muscle_group_ids = sorted([item.id for item in workout_muscle_groups])
                if current_muscle_group_ids != expected_muscle_group_ids:
                    await workout.muscle_groups.clear(using_db=conn)
                    if workout_muscle_groups:
                        await workout.muscle_groups.add(*workout_muscle_groups, using_db=conn)

        print(
            "[dummy-equipment] seeding completed "
            f"(categories_created={category_created}, equipment_groups_created={equipment_group_created}, "
            f"muscle_groups_created={muscle_group_created}, "
            f"workouts_created={workout_created}, workouts_updated={workout_updated})"
        )
    except Exception as error:
        print(f"[dummy-equipment] seeding failed: {error}")
