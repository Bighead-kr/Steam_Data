"""Hand-written Steam Store API (appdetails) + SteamSpy response samples.

Shape: raw = {"appdetails": {...}, "steamspy": {...}}. This is the dict
stored verbatim in games_raw.raw_json and consumed by normalize_game().
"""

RAW_ROGUELIKE = (
    100001,
    {
        "appdetails": {
            "name": "Dungeon of Echoes",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 1999},
            "genres": [{"id": "23", "description": "Indie"}, {"id": "3", "description": "RPG"}],
            "release_date": {"coming_soon": False, "date": "Mar 12, 2021"},
        },
        "steamspy": {
            "genre": "Indie, RPG, Roguelike",
            "tags": {"Roguelike": 900, "Indie": 500, "Pixel Graphics": 200},
            "positive": 4200,
            "negative": 300,
            "owners": "100,000 .. 200,000",
            "average_forever": 480,
        },
    },
)

RAW_FREE_TO_PLAY = (
    100002,
    {
        "appdetails": {
            "name": "Free Roguelite Arena",
            "type": "game",
            "is_free": True,
            "genres": [{"id": "23", "description": "Indie"}],
            "release_date": {"coming_soon": False, "date": "Jan 1, 2022"},
        },
        "steamspy": {
            "genre": "Indie, Roguelike",
            "tags": {"Roguelike": 300, "Free to Play": 150},
            "positive": 800,
            "negative": 200,
            "owners": "1,000,000 .. 2,000,000",
            "average_forever": 120,
        },
    },
)

RAW_DLC = (
    100003,
    {
        "appdetails": {
            "name": "Dungeon of Echoes: Soundtrack",
            "type": "dlc",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 499},
            "genres": [{"id": "23", "description": "Indie"}],
            "release_date": {"coming_soon": False, "date": "Mar 12, 2021"},
        },
        "steamspy": {
            "genre": "Indie",
            "tags": {},
            "positive": 10,
            "negative": 0,
            "owners": "20,000 .. 50,000",
            "average_forever": 0,
        },
    },
)

RAW_MISSING_RELEASE_DATE = (
    100004,
    {
        "appdetails": {
            "name": "Untitled Management Sim",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 1499},
            "genres": [{"id": "28", "description": "Simulation"}],
            "release_date": {"coming_soon": True, "date": ""},
        },
        "steamspy": {
            "genre": "Simulation",
            "tags": {"Management": 50},
            "positive": 5,
            "negative": 1,
            "owners": "0 .. 20,000",
            "average_forever": 0,
        },
    },
)

RAW_LOW_REVIEW_COUNT = (
    100005,
    {
        "appdetails": {
            "name": "Tiny Roguelike Gem",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 999},
            "genres": [{"id": "23", "description": "Indie"}, {"id": "3", "description": "RPG"}],
            "release_date": {"coming_soon": False, "date": "Jun 5, 2021"},
        },
        "steamspy": {
            "genre": "Indie, Roguelike",
            "tags": {"Roguelike": 5, "Indie": 3},
            "positive": 3,
            "negative": 0,
            "owners": "0 .. 20,000",
            "average_forever": 600,
        },
    },
)

RAW_APPDETAILS_NULL = (
    100007,
    {
        # Steam's appdetails API returns {"success": false} (no "data" key)
        # for delisted/invalid app ids; a collector that stores that verbatim
        # would end up with appdetails: null here rather than the key being
        # absent entirely - both are plausible, but null is the shape we
        # guard against explicitly in normalize_game().
        "appdetails": None,
        "steamspy": {
            "genre": "Indie",
            "tags": {"Indie": 10},
            "positive": 5,
            "negative": 1,
            "owners": "0 .. 20,000",
            "average_forever": 0,
        },
    },
)

RAW_PRICE_OVERVIEW_NULL = (
    100008,
    {
        "appdetails": {
            "name": "Paid Game Missing Price",
            "type": "game",
            "is_free": False,
            "price_overview": None,
            "genres": [{"id": "23", "description": "Indie"}],
            "release_date": {"coming_soon": False, "date": "Jul 3, 2019"},
        },
        "steamspy": {
            "genre": "Indie",
            "tags": {"Indie": 10},
            "positive": 50,
            "negative": 5,
            "owners": "20,000 .. 50,000",
            "average_forever": 100,
        },
    },
)

RAW_STEAMSPY_TAGS_ARRAY = (
    100009,
    {
        "appdetails": {
            "name": "No Tags Yet",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 999},
            "genres": [{"id": "23", "description": "Indie"}],
            "release_date": {"coming_soon": False, "date": "Aug 15, 2020"},
        },
        "steamspy": {
            "genre": "Indie",
            "tags": [],  # SteamSpy returns an array (not an object) when there are no tags
            "positive": 20,
            "negative": 2,
            "owners": "0 .. 20,000",
            "average_forever": 30,
        },
    },
)

RAW_MALFORMED_RECORD = (
    100010,
    {
        # release_date is a bare string instead of the expected
        # {"coming_soon": ..., "date": ...} object - a genuinely malformed/
        # unexpected API shape that normalize_game() has no specific defense
        # for, and should be caught and skipped by the pipeline rather than
        # aborting the whole normalizer batch.
        "appdetails": {
            "name": "Malformed Record",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 999},
            "genres": [{"id": "23", "description": "Indie"}],
            "release_date": "not-a-dict",
        },
        "steamspy": {
            "genre": "Indie",
            "tags": {"Indie": 5},
            "positive": 5,
            "negative": 1,
            "owners": "0 .. 20,000",
            "average_forever": 0,
        },
    },
)

RAW_GENRE_STRING_ONLY = (
    100006,
    {
        "appdetails": {
            "name": "Farm Manager Deluxe",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 2499},
            "genres": [],
            "release_date": {"coming_soon": False, "date": "Nov 20, 2020"},
        },
        "steamspy": {
            "genre": "Simulation, Management",
            "tags": {},
            "positive": 600,
            "negative": 100,
            "owners": "50,000 .. 100,000",
            "average_forever": 300,
        },
    },
)
