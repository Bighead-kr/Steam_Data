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
            "release_date": {"coming_soon": False, "date": "12 Mar, 2021"},
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
            "release_date": {"coming_soon": False, "date": "1 Jan, 2022"},
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
            "release_date": {"coming_soon": False, "date": "12 Mar, 2021"},
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
            "release_date": {"coming_soon": False, "date": "5 Jun, 2021"},
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

RAW_GENRE_STRING_ONLY = (
    100006,
    {
        "appdetails": {
            "name": "Farm Manager Deluxe",
            "type": "game",
            "is_free": False,
            "price_overview": {"currency": "USD", "final": 2499},
            "genres": [],
            "release_date": {"coming_soon": False, "date": "20 Nov, 2020"},
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
