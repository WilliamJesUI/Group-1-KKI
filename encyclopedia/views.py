from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from plants.models import Plant

from .models import PlantCollection, SavedPlant


# Practical notes supplement for each species of plants.
# Trefle data is probably be incomplete, thus each known plant has useful starter advice.
PLANT_TIPS = {
    "tomato": [
        "Bury the stem a little deeper when transplanting so extra roots can form.",
        "Use a stake or cage early, and pick fruits when fully coloured and slightly yielding.",
    ],
    "potato": [
        "Hill loose soil around stems as they grow so developing tubers stay covered.",
        "Grow in a deep container and stop watering heavily as the foliage begins to die back.",
    ],
    "chili-pepper": [
        "Start in a warm, bright position and use a pot with excellent drainage.",
        "Harvest peppers with clean snips; regular picking encourages continued fruiting.",
    ],
    "birds-eye-chili": [
        "Give the compact plant warmth and airflow, especially in humid weather.",
        "Pick the small pods regularly and avoid keeping the potting mix constantly soggy.",
    ],
    "eggplant": [
        "Use a sturdy container and support branches once fruits become heavy.",
        "Harvest glossy fruits while the skin is firm; overripe fruit becomes dull and seedy.",
    ],
    "lettuce": [
        "Choose a cooler, partly shaded spot in hot weather to slow bolting.",
        "Harvest outer leaves first for a cut-and-come-again supply.",
    ],
    "spinach": [
        "Keep the root zone evenly moist so leaves stay tender.",
        "Pick young leaves often and provide afternoon shade when temperatures rise.",
    ],
    "water-spinach": [
        "Keep the soil consistently moist; this leafy crop dislikes drying out.",
        "Cut tender shoot tips above a leaf node to encourage branching.",
    ],
    "bok-choy": [
        "Keep growth steady with regular moisture to reduce premature flowering.",
        "Harvest whole small heads or remove outer leaves while the centre continues growing.",
    ],
    "cabbage": [
        "Give the head room to develop and check leaf undersides for caterpillars.",
        "Water at soil level and harvest when the head feels firm.",
    ],
    "carrot": [
        "Sow directly into deep, stone-free soil because taproots dislike transplanting.",
        "Thin seedlings early so neighbouring roots have room to swell.",
    ],
    "cucumber": [
        "Provide a trellis to keep vines and fruits off damp ground.",
        "Water deeply and consistently; uneven moisture can make fruit bitter or misshapen.",
    ],
    "long-bean": [
        "Install a tall trellis before the climbing vines spread.",
        "Pick pods while young and tender to encourage more flowers.",
    ],
    "green-bean": [
        "Sow after the soil is warm and avoid disturbing roots during cultivation.",
        "Harvest pods before seeds bulge for the best texture and continued production.",
    ],
    "onion": [
        "Use a sunny bed with loose soil and avoid excess nitrogen late in growth.",
        "Reduce watering as tops fall over, then cure bulbs in a dry, airy place.",
    ],
    "garlic": [
        "Plant individual cloves pointed end up in loose, well-drained soil.",
        "Let the foliage yellow naturally before lifting bulbs, then dry them thoroughly.",
    ],
    "spring-onion": [
        "Sow in short rows every few weeks for a staggered supply.",
        "Snip outer greens or pull whole stems once they reach the size you prefer.",
    ],
    "sweet-potato": [
        "Give trailing vines room or guide them over the edge of a large container.",
        "Harvest carefully to avoid bruising the storage roots, then cure them before storing.",
    ],
    "corn": [
        "Plant in a block rather than a single row to improve wind pollination.",
        "Keep moisture steady when tassels and silks appear, the key period for kernel formation.",
    ],
    "pumpkin": [
        "Allow plenty of space for sprawling vines and set developing fruits on dry mulch.",
        "Leave a short stem when harvesting and let the rind harden before storage.",
    ],
    "okra": [
        "Sow in warm soil and give the plant space for its tall, branching form.",
        "Pick pods while small and tender, usually every day or two in productive weather.",
    ],
    "sweet-basil": [
        "Pinch the growing tips above a pair of leaves to make a bushier plant.",
        "Remove flower spikes if you want to keep producing tender leaves.",
    ],
    "mint": [
        "Grow mint in its own pot because underground runners spread aggressively.",
        "Harvest stems regularly and keep the potting mix evenly moist.",
    ],
    "peppermint": [
        "Contain the roots in a pot and place it where it gets bright light without harsh all-day heat.",
        "Cut stems just above a leaf pair to encourage fresh side shoots.",
    ],
    "rosemary": [
        "Use a gritty, fast-draining mix and let the top layer dry between waterings.",
        "Trim soft tips lightly; avoid cutting deeply into old woody stems.",
    ],
    "thyme": [
        "Choose a sunny spot with excellent drainage; wet roots are its main enemy.",
        "Harvest small sprigs before flowering for a compact, leafy plant.",
    ],
    "oregano": [
        "Let the surface of the soil dry slightly between waterings.",
        "Trim the tips often to prevent legginess and encourage branching.",
    ],
    "parsley": [
        "Keep the soil evenly moist while seeds germinate, which can be slow.",
        "Cut the outer stems at the base and leave the centre crown intact.",
    ],
    "coriander": [
        "Sow directly where it will grow because it dislikes root disturbance.",
        "Use partial afternoon shade in hot weather to delay bolting.",
    ],
    "dill": [
        "Sow in its final position and protect the tall stems from strong wind.",
        "Harvest leaves before flowering or leave umbels to form seeds.",
    ],
    "chives": [
        "Divide crowded clumps every few years to keep growth vigorous.",
        "Snip leaves close to the base and leave enough foliage for regrowth.",
    ],
    "lemongrass": [
        "Give the clump a wide pot and plenty of warmth and sun.",
        "Harvest outer stalks near the base while leaving the centre to keep growing.",
    ],
    "ginger": [
        "Plant a plump rhizome shallowly in rich, loose soil with buds facing upward.",
        "Keep it warm and moist, but reduce watering when the leaves naturally die back.",
    ],
    "turmeric": [
        "Use a wide pot and loose, compost-rich soil for the spreading rhizomes.",
        "Keep warm and moist during active growth, then allow a drier rest as foliage fades.",
    ],
    "galangal": [
        "Provide warmth, humidity and a roomy container for rhizome development.",
        "Use a loose mix that holds some moisture but drains freely after watering.",
    ],
    "pandan": [
        "Place in bright filtered light and protect from harsh afternoon sun.",
        "Keep moisture consistent and harvest mature outer leaves rather than the centre spear.",
    ],
    "sage": [
        "Give it sun and a free-draining potting mix; avoid frequent small waterings.",
        "Prune lightly after flowering, but do not cut far into bare old wood.",
    ],
    "lavender": [
        "Use a gritty alkaline-leaning mix and strong airflow around the foliage.",
        "Remove spent flower stems and avoid rich, constantly damp soil.",
    ],
    "aloe-vera": [
        "Use cactus mix and a pot with drainage holes; water only after the mix dries.",
        "Keep the rosette above the soil line and remove offsets when they have roots.",
    ],
    "moringa": [
        "Choose a deep container or sunny bed because the plant develops a strong root system.",
        "Prune the leader when young if you want a shorter, leafier tree.",
    ],
    "makrut-lime": [
        "Use a large draining pot, bright sun and regular feeding during active growth.",
        "Check leaf undersides for pests and harvest only the leaves you need.",
    ],
    "rose": [
        "Give the plant morning sun and space for air to move through the foliage.",
        "Remove spent blooms and water at the base to help limit leaf disease.",
    ],
    "marigold": [
        "Deadhead faded flowers to keep new blooms coming.",
        "Avoid overly rich soil, which can produce lots of leaves but fewer flowers.",
    ],
    "sunflower": [
        "Sow where the plant can receive direct sun and shelter tall stems from wind.",
        "Water deeply while the stem and flower head are developing.",
    ],
    "zinnia": [
        "Provide sun and good spacing; crowded foliage stays damp longer.",
        "Cut flowers above a leaf pair to encourage more branching blooms.",
    ],
    "arabian-jasmine": [
        "Provide warmth, bright light and a support or shape for its woody stems.",
        "Keep moisture even during bud formation and prune lightly after flowering.",
    ],
    "petunia": [
        "Use a free-draining pot and give trailing varieties room to spill over the edge.",
        "Remove faded blooms and feed lightly during the flowering season.",
    ],
    "cosmos": [
        "Grow in a sunny spot with modest soil fertility to avoid floppy stems.",
        "Deadhead regularly or leave a few flower heads to produce seed.",
    ],
    "bougainvillea": [
        "Use a very free-draining mix and allow it to dry somewhat between waterings.",
        "Bright sun and restrained feeding usually encourage more colourful bracts.",
    ],
    "chrysanthemum": [
        "Pinch young shoots to build a bushy shape before buds form.",
        "Water the soil rather than the leaves and remove spent flowers.",
    ],
    "periwinkle": [
        "It tolerates heat once established, but young plants need steady moisture.",
        "Trim long stems to keep the groundcover compact and encourage new growth.",
    ],
    "ixora": [
        "Use slightly acidic soil and avoid hard, alkaline water if leaves yellow.",
        "Give it warmth and consistent moisture while flower clusters are forming.",
    ],
    "nasturtium": [
        "Sow directly and keep feeding modest; rich soil favours leaves over flowers.",
        "Leaves and flowers are edible, but only eat plants grown without unsafe chemicals.",
    ],
    "snapdragon": [
        "Choose a cooler bright position and provide support for tall flower spikes.",
        "Remove spent spikes to encourage side shoots and a longer display.",
    ],
    "gerbera": [
        "Keep the crown slightly above the soil and provide excellent drainage.",
        "Remove old leaves at the base and water early so foliage dries before night.",
    ],
    "pot-marigold": [
        "Grow in sun with moderate watering and remove faded flower heads.",
        "Harvest petals only from correctly identified plants grown without chemical sprays.",
    ],
    "morning-glory": [
        "Set up a trellis before vines start climbing and give roots room.",
        "Water regularly while establishing; once mature, avoid leaving roots waterlogged.",
    ],
    "peace-lily": [
        "Place in bright indirect light and keep it away from strong direct sun.",
        "Water when the surface begins to dry; drooping leaves often signal thirst, but check soil first.",
    ],
    "moth-orchid": [
        "Use orchid bark rather than ordinary potting soil and keep the crown ventilated.",
        "Water when the medium is nearly dry, then drain completely; never leave the pot standing in water.",
    ],
    "dahlia": [
        "Plant tubers in warm soil and provide support for tall varieties.",
        "Water deeply once shoots are established and deadhead flowers as they fade.",
    ],
    "tulip": [
        "Tulips need a cool rest period and may perform best as seasonal bulbs in warm climates.",
        "Use a draining container and keep bulbs cool and dry after foliage dies back.",
    ],
}


def care_guide_for(plant):
    """Build a plant-specific guide from its identity and saved care attributes."""
    tips = PLANT_TIPS.get(
        plant.slug,
        [
            f"Start {plant.name} in a clean container or bed with drainage suited to its roots.",
            f"Check {plant.name.lower()} weekly for new growth, pests and signs of water stress.",
        ],
    )

    if plant.sunlight == "full_sun":
        light_note = (
            "Choose a spot with direct sun for most of the day. In very hot weather, "
            "watch for afternoon wilting."
        )
    elif plant.sunlight == "full_sun_part_shade":
        light_note = (
            "Aim for a bright position with sun for part of the day; some afternoon "
            "shade can help in hot weather."
        )
    elif plant.sunlight == "part_shade":
        light_note = (
            "Give it bright filtered light or gentle morning sun, avoiding harsh "
            "afternoon exposure."
        )
    elif plant.sunlight == "shade":
        light_note = (
            "Choose a sheltered shaded position with good ambient light rather than "
            "deep darkness."
        )
    else:
        light_note = (
            "Start in bright light and adjust the position based on the plant's response."
        )

    interval = plant.watering_every
    if interval:
        water_note = (
            f"The saved care estimate suggests checking moisture about every {interval}; "
            "climate, pot size and rain can change this."
        )
    elif plant.watering == "minimum":
        water_note = (
            "Let the potting mix dry substantially between waterings, and never leave "
            "the roots sitting in water."
        )
    elif plant.watering == "frequent":
        water_note = (
            "Check the soil often and water when the surface begins to dry; containers "
            "can dry quickly in warm weather."
        )
    else:
        water_note = (
            "Water when the top layer begins to dry, then let excess water drain away."
        )

    category_label = (
        plant.get_category_display().lower() if plant.category else "garden"
    )
    first_tip = tips[0] if tips else "observe its growing conditions"
    overview = (
        f"{plant.name} is included in the {category_label} directory. "
        f"A useful first step is to {first_tip[0].lower() + first_tip[1:]}"
    )

    return {
        "overview": overview,
        "specific_tips": tips,
        "light_note": light_note,
        "water_note": water_note,
        "care_is_estimated": plant.care_estimated,
        "source_label": plant.info_source or "Grow Your Garden care notes",
    }


def _require_authenticated(request):
    """Keep collection actions private without depending on a login-page app."""
    if not request.user.is_authenticated:
        messages.info(
            request,
            "Sign-in is required to view or manage plant collections.",
        )
        return False
    return True


def encyclopedia(request):
    """Show the searchable, filterable plant directory."""
    plants = Plant.objects.all()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "all").strip().lower()
    difficulty = request.GET.get("difficulty", "").strip().lower()

    if query:
        plants = plants.filter(
            Q(name__icontains=query)
            | Q(scientific_name__icontains=query)
            | Q(family__icontains=query)
        )
    if category in {"herbs", "vegetables", "flowers"}:
        plants = plants.filter(category=category)
    if difficulty in {"easy", "medium", "hard"}:
        plants = plants.filter(difficulty=difficulty)

    collections = PlantCollection.objects.none()
    saved_ids = set()
    if request.user.is_authenticated:
        collections = PlantCollection.objects.filter(user=request.user)
        saved_ids = set(
            PlantCollection.objects.filter(
                user=request.user,
                plants__isnull=False,
            ).values_list("plants__id", flat=True)
        )

    return render(
        request, "encyclopedia.html", {
            "plants": plants,
            "query": query,
            "category": category,
            "difficulty": difficulty,
            "saved_ids": saved_ids,
            "collections": collections,
            "plant_count": Plant.objects.count(),
            "result_count": plants.count(),
        },
    )


def plant_detail(request, slug):
    """Display a plant's detail page and its growing guide."""
    plant = get_object_or_404(Plant, slug=slug)
    collections = (
        PlantCollection.objects.filter(user=request.user)
        if request.user.is_authenticated
        else PlantCollection.objects.none()
    )
    saved_ids = (
        set(collections.filter(plants=plant).values_list("id", flat=True))
        if request.user.is_authenticated
        else set()
    )

    return render(
        request, "plant_detail.html", {
            "plant": plant,
            "is_saved": bool(saved_ids),
            "saved_collection_ids": saved_ids,
            "collections": collections,
            "care_guide": care_guide_for(plant),
        },
    )


@require_POST
def toggle_saved(request, slug):
    """Add or remove a plant from the collection selected by the current user."""
    if not request.user.is_authenticated:
        messages.info(request, "Plant collections require authentication.")
        return redirect(request.POST.get("next") or "encyclopedia:index")

    plant = get_object_or_404(Plant, slug=slug)
    collection_id = request.POST.get("collection_id", "").strip()
    collection = get_object_or_404(
        PlantCollection,
        pk=collection_id,
        user=request.user,
    )

    if collection.plants.filter(pk=plant.pk).exists():
        collection.plants.remove(plant)
        # Keep the bookmark record while the plant remains in any other collection.
        if not PlantCollection.objects.filter(user=request.user, plants=plant).exists():
            SavedPlant.objects.filter(user=request.user, plant=plant).delete()
        messages.success(request, f"{plant.name} removed from {collection.name}.")
    else:
        collection.plants.add(plant)
        SavedPlant.objects.get_or_create(user=request.user, plant=plant)
        messages.success(request, f"{plant.name} saved to {collection.name}.")

    return redirect(request.POST.get("next") or "encyclopedia:index")


@require_POST
def create_collection(request):
    """Create a collection for the authenticated user."""
    if not _require_authenticated(request):
        return redirect("encyclopedia:index")

    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Enter a name for your new collection.")
    else:
        collection = PlantCollection.objects.create(
            user=request.user,
            name=name[:100],
        )
        messages.success(request, f'Collection "{collection.name}" created.')
        return redirect(f"/encyclopedia/collection/?collection={collection.pk}")

    return redirect("encyclopedia:collection")


@require_POST
def delete_collection(request, collection_id):
    """Delete one collection owned by the authenticated user."""
    if not _require_authenticated(request):
        return redirect("encyclopedia:index")

    collection = get_object_or_404(
        PlantCollection,
        pk=collection_id,
        user=request.user,
    )
    name = collection.name
    collection.delete()
    messages.success(request, f'Collection "{name}" deleted.')
    return redirect("encyclopedia:collection")


def my_collection(request):
    """Show the user's collections and handle collection renaming."""
    if not _require_authenticated(request):
        return redirect("encyclopedia:index")

    collections = PlantCollection.objects.filter(user=request.user)
    active_id = request.GET.get("collection", "").strip()
    active_collection = (
        collections.filter(pk=active_id).first() if active_id else collections.first()
    )

    if request.method == "POST":
        collection_id = request.POST.get("collection_id", "").strip()
        collection = get_object_or_404(
            PlantCollection,
            pk=collection_id,
            user=request.user,
        )
        name = request.POST.get("name", "").strip()
        if name:
            collection.name = name[:100]
            collection.save()
            messages.success(request, "Collection name updated.")
        else:
            messages.error(request, "Please enter a collection name.")
        return redirect(f"/encyclopedia/collection/?collection={collection.pk}")

    return render(
        request, "collection.html", {
            "collections": collections,
            "collection": active_collection,
        },
    )


@require_POST
def remove_from_collection(request, slug):
    """Remove a plant from one collection and clean up its saved bookmark if needed."""
    if not request.user.is_authenticated:
        messages.info(request, "Plant collections require authentication.")
        return redirect("encyclopedia:index")

    plant = get_object_or_404(Plant, slug=slug)
    collection_id = request.POST.get("collection_id", "").strip()
    collection = get_object_or_404(
        PlantCollection,
        pk=collection_id,
        user=request.user,
    )
    collection.plants.remove(plant)

    if not PlantCollection.objects.filter(user=request.user, plants=plant).exists():
        SavedPlant.objects.filter(user=request.user, plant=plant).delete()

    messages.success(request, f"{plant.name} removed from {collection.name}.")
    return redirect(f"/encyclopedia/collection/?collection={collection.pk}")
