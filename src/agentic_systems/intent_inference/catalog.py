"""Shared catalog: intent labels, training utterances, situation prototypes,
tool registry, stub-agent roster, and the fixed evaluation test suite.

Everything is deterministic and hand-authored; the test suite is frozen so
both architectures are graded on identical ground.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Traditional intent catalog (the "predefined buckets")
# ---------------------------------------------------------------------------
INTENTS = [
    "check_balance",
    "transfer_money",
    "reset_password",
    "update_phone",
    "book_flight",
    "cancel_booking",
    "track_order",
    "laptop_support",
    "wifi_help",
    "book_hotel",
    "interview_prep",
    "restaurant_suggestion",
]

# Canonical training utterances per intent — clean, on-rails phrasings of the
# kind a traditional bot team would label.  The test suite deliberately
# contains paraphrases with low lexical overlap.
TRAIN_UTTERANCES = {
    "check_balance": [
        "What is my account balance?",
        "Show me my balance",
        "I want to check my balance",
        "Display my current balance",
        "How much is in my account?",
        "Balance inquiry please",
        "Tell me my checking account balance",
        "I need to see my balance",
    ],
    "transfer_money": [
        "Transfer $200 to my savings account",
        "Send money to John",
        "I want to make a transfer",
        "Move $50 from checking to savings",
        "Wire funds to my broker",
        "Transfer money between my accounts",
    ],
    "reset_password": [
        "I forgot my password",
        "Reset my password please",
        "I need to change my password",
        "Help me recover my password",
        "I lost my password",
        "Password reset request",
    ],
    "update_phone": [
        "I changed my phone number",
        "Update my phone number",
        "My number is now 555-0100, please update it",
        "Change the phone number on my account",
        "I have a new mobile number",
    ],
    "book_flight": [
        "Book a flight to Denver",
        "I need a plane ticket to Boston",
        "Find me flights for next Friday",
        "Reserve a flight to Seattle",
        "I want to fly to Austin tomorrow",
    ],
    "cancel_booking": [
        "Cancel my booking",
        "I want to cancel my reservation",
        "Please cancel my flight",
        "Abort my booking",
        "I need to cancel my trip",
    ],
    "track_order": [
        "Where is my order?",
        "Track my package",
        "What is the status of my delivery?",
        "I want to track my shipment",
        "Order tracking please",
    ],
    "laptop_support": [
        "My laptop is not working",
        "I need help with my laptop",
        "My computer screen is broken",
        "Laptop technical support",
        "My laptop keeps crashing",
    ],
    "wifi_help": [
        "My wifi is not working",
        "I forgot my wifi password",
        "Help me connect to wifi",
        "Wifi connection problem",
        "I cannot connect to the internet",
    ],
    "book_hotel": [
        "Book a hotel in Chicago",
        "I need a hotel reservation",
        "Find me a hotel for two nights",
        "Reserve a hotel room downtown",
        "Hotel booking please",
    ],
    "interview_prep": [
        "Help me prepare for my interview",
        "I have a job interview coming up",
        "Interview preparation tips",
        "How do I prepare for an interview?",
    ],
    "restaurant_suggestion": [
        "Recommend a good restaurant",
        "Where should I eat tonight?",
        "Suggest a place for dinner",
        "Find me a nearby restaurant",
        "I want restaurant recommendations",
    ],
}

# ---------------------------------------------------------------------------
# Situation prototypes for the inference pipeline.
# Each prototype is (prototype_id, description, goal_ids it evidences).
# The pipeline matches utterances to prototypes in embedding space; intent is
# never a direct classification target.
# ---------------------------------------------------------------------------
PROTOTYPES = [
    ("sit_balance_check", "user wants to know how much money is in their bank account right now", ["check_balance"]),
    ("sit_spending_capacity", "user wonders whether they have enough money available to afford a purchase or expense", ["check_balance"]),
    ("sit_transfer", "user wants to move money from one account to another or send money to someone", ["transfer_money"]),
    ("sit_pwd_forgot", "user cannot log in because they forgot or lost their password", ["reset_password"]),
    ("sit_phone_changed", "user got a new phone number and needs it updated so they can receive codes", ["update_phone", "auth_assistance"]),
    ("sit_otp_blocked", "user cannot receive one time passcodes and is locked out of authentication", ["auth_assistance"]),
    ("sit_flight_book", "user wants to reserve a flight or plane ticket to a destination", ["book_flight"]),
    ("sit_booking_cancel", "user wants to cancel an existing reservation or booking", ["cancel_booking"]),
    ("sit_order_track", "user wants the status or location of a package or order", ["track_order"]),
    ("sit_laptop_display", "user laptop screen has a display problem such as going dark after login", ["diagnose_display"]),
    ("sit_laptop_thermal", "user laptop is overheating or running hot", ["laptop_support"]),
    ("sit_wifi_pwd", "user forgot wifi password or cannot connect to wireless network", ["wifi_help"]),
    ("sit_hotel_book", "user wants to reserve a hotel room for a trip", ["book_hotel"]),
    ("sit_hotel_cheaper", "user wants to modify an existing hotel search to lower the price", ["book_hotel", "refine_search"]),
    ("sit_interview_prep", "user has a job interview coming and wants preparation help", ["interview_prep"]),
    ("sit_interview_attire", "user asks what clothing to wear for an occasion such as an interview", ["interview_prep", "attire_advice"]),
    ("sit_hungry", "user is hungry and needs food, a meal, a recipe, or a restaurant", ["food_need"]),
    ("sit_restaurant", "user wants a recommendation for where to eat", ["restaurant_suggestion"]),    ("sit_router_haiku", "user wants a short creative poem about a household device", ["creative_writing"]),
    ("sit_account_locked", "user is locked out of their account and needs access restored", ["reset_password", "auth_assistance"]),
]

# Prototype gating: a prototype only counts when its discriminative terms are
# present (after synonym expansion).  This stops "forgot my password" from
# matching the wifi prototype, etc.  General mechanism, not per-test tuning:
# each situation has necessary participants.
PROTO_REQUIRES = {
    "sit_balance_check": {"balance", "money", "account", "afford", "funds", "cash"},
    "sit_spending_capacity": {"afford", "money", "balance", "budget", "cost"},
    "sit_transfer": {"transfer", "send", "move", "wire", "bucks"},
    "sit_pwd_forgot": {"password", "passcode", "login"},
    "sit_phone_changed": {"phone", "number", "mobile"},
    "sit_otp_blocked": {"otp", "passcode", "code", "authentication", "locked"},
    "sit_flight_book": {"flight", "fly", "plane", "ticket"},
    "sit_booking_cancel": {"cancel", "cancelled", "abort"},
    "sit_order_track": {"order", "package", "track", "delivery", "shipment", "status"},
    "sit_laptop_display": {"laptop", "computer", "macbook", "screen", "display", "monitor"},
    "sit_laptop_thermal": {"laptop", "computer", "macbook", "overheating", "hot", "heat", "fan"},
    "sit_wifi_pwd": {"wifi", "wireless", "internet", "network"},
    "sit_hotel_book": {"hotel"},
    "sit_hotel_cheaper": {"hotel", "cheaper", "cheap", "price", "cost"},
    "sit_interview_prep": {"interview"},
    "sit_interview_attire": {"wear", "clothing", "attire", "dress", "outfit"},
    "sit_hungry": {"hungry", "starving", "eat", "lunch", "dinner", "food", "meal"},
    "sit_restaurant": {"restaurant"},
    "sit_router_haiku": {"haiku", "poem", "poetry", "router"},
    "sit_account_locked": {"locked", "access"},
}

# Predicate-level disambiguation: when the main predicate is financial,
# food readings of a secondary noun ("lunch") are suppressed, and vice
# versa.  "Can you afford lunch?" is about money, not hunger.
FINANCIAL_PREDICATES = {"afford", "cost", "price", "balance", "pay", "buy",
                        "purchase", "cheap", "cheaper", "expensive", "budget"}
HUNGER_PREDICATES = {"hungry", "starving", "craving"}

# Small synonym expansion so the embedding space captures paraphrase
# neighborhoods without a neural model.
SYNONYMS = {
    "afford": ["money", "balance", "cost", "price", "budget"],
    "hungry": ["food", "eat", "meal", "restaurant", "dinner"],
    "starving": ["food", "eat", "meal", "hungry"],
    "broke": ["money", "balance", "poor"],
    "lunch": ["food", "meal", "eat", "restaurant"],
    "dinner": ["food", "meal", "eat", "restaurant"],
    "eat": ["food", "meal", "restaurant", "hungry"],
    "dark": ["display", "screen", "blank", "black"],
    "blank": ["display", "screen", "dark"],
    "overheating": ["hot", "thermal", "heat", "fan"],
    "hot": ["thermal", "heat", "overheating"],
    "cheaper": ["cheap", "price", "cost", "budget", "discount"],
    "cheap": ["cheaper", "price", "cost", "budget"],
    "wear": ["clothing", "attire", "dress", "outfit"],
    "clothing": ["wear", "attire", "dress", "outfit"],
    "dress": ["wear", "clothing", "attire"],
    "haiku": ["poem", "poetry", "creative", "write"],
    "poem": ["haiku", "poetry", "creative"],
    "forgot": ["forgotten", "lost", "remember"],
    "receive": ["get", "obtain"],
    "money": ["balance", "funds", "cash", "afford"],
    "password": ["credentials", "login", "passcode"],
    "phone": ["mobile", "number", "telephone"],
}

# ---------------------------------------------------------------------------
# Tool registry + stub agent roster (enterprise pipeline stages)
# ---------------------------------------------------------------------------
TOOLS = {
    "account_api.balance": ["check_balance"],
    "account_api.transfer": ["transfer_money"],
    "auth_api.reset_password": ["reset_password"],
    "auth_api.update_phone": ["update_phone"],
    "auth_api.verify_identity": ["auth_assistance"],
    "booking_api.flights": ["book_flight"],
    "booking_api.cancel": ["cancel_booking"],
    "booking_api.hotels": ["book_hotel"],
    "shipping_api.track": ["track_order"],
    "diag_tool.display": ["diagnose_display"],
    "diag_tool.thermal": ["diagnose_thermal"],
    "net_tool.wifi": ["wifi_help"],
    "kb.search": ["interview_prep", "attire_advice", "food_need", "restaurant_suggestion"],
    "llm.generate": ["creative_writing"],
}

STUB_AGENTS = {
    "AccountAgent": ["check_balance", "transfer_money"],
    "AuthAgent": ["reset_password", "update_phone", "auth_assistance"],
    "BookingAgent": ["book_flight", "cancel_booking", "book_hotel", "refine_search", "track_order"],
    "SupportAgent": ["laptop_support", "diagnose_display", "diagnose_thermal", "wifi_help"],
    "LifestyleAgent": ["interview_prep", "attire_advice", "food_need", "restaurant_suggestion", "creative_writing"],
}

# ---------------------------------------------------------------------------
# Fixed evaluation test suite.
# Each case: id, turns (list of user utterances), expected goal ids
# (multiset across the conversation), phenomena tags, and grading notes.
# ---------------------------------------------------------------------------
TEST_SUITE = [
    # --- paraphrase robustness (phenomenon 1) ---
    dict(id="p1", turns=["I want to know my balance"], expect={"check_balance"},
         tags=["paraphrase"], note="canonical phrasing"),
    dict(id="p2", turns=["How much money do I have?"], expect={"check_balance"},
         tags=["paraphrase"], note="canonical phrasing"),
    dict(id="p3", turns=["Can you tell me whether I can afford lunch today?"],
         expect={"check_balance"}, tags=["paraphrase"],
         note="low lexical overlap with training data"),
    dict(id="p4", turns=["Transfer $200 to my savings account"], expect={"transfer_money"},
         tags=["paraphrase"], note="canonical"),
    dict(id="p5", turns=["Could you move two hundred bucks into savings for me?"],
         expect={"transfer_money"}, tags=["paraphrase"],
         note="slang + number words, low overlap"),
    # --- multi-intent (phenomenon 2) ---
    dict(id="m1", turns=["I forgot my password, but I also changed my phone number, and I can't receive OTP"],
         expect={"reset_password", "update_phone", "auth_assistance"},
         tags=["multi_intent"], note="triple intent from the concept"),
    dict(id="m2", turns=["My laptop is overheating and I also forgot my Wi-Fi password"],
         expect={"laptop_support", "wifi_help"},
         tags=["multi_intent"], note="two problems, one utterance"),
    dict(id="m3", turns=["Cancel my booking and book a flight to Denver"],
         expect={"cancel_booking", "book_flight"},
         tags=["multi_intent"], note="cancel + book"),
    # --- latent / implicit intent (phenomenon 3) ---
    dict(id="l1", turns=["I'm hungry"], expect={"food_need"},
         tags=["latent"], note="no explicit request; goal must be inferred"),
    dict(id="l2", turns=["I have an interview tomorrow"], expect={"interview_prep"},
         tags=["latent"], note="statement of fact, goal inferred"),
    # --- dynamic intent over turns (phenomenon 4) ---
    dict(id="d1", turns=["I have an interview tomorrow", "What should I wear?"],
         expect={"interview_prep", "attire_advice"},
         tags=["dynamic", "context"],
         note="turn 2 meaningless without turn 1"),
    # --- context-dependent meaning (phenomenon 5) ---
    dict(id="c1", turns=["Book me a hotel in Chicago", "Make it cheaper"],
         expect={"book_hotel", "refine_search"},
         tags=["context"],
         note="'cheaper' only meaningful against prior hotel search"),
    dict(id="c2", turns=["Track my package", "Actually cancel it"],
         expect={"track_order", "cancel_booking"},
         tags=["context"],
         note="'it' resolves to the order; new goal cancel"),
    # --- out-of-catalog (phenomenon 6) ---
    dict(id="o1", turns=["Can you write a haiku about my router?"],
         expect={"creative_writing"}, tags=["out_of_catalog"],
         note="no catalog intent; must not crash or say 'unknown'"),
    dict(id="o2", turns=["My Apple laptop screen becomes dark after login"],
         expect={"diagnose_display"}, tags=["out_of_catalog", "missing_info"],
         note="canonical example; expect missing-info questions: external monitor? safe mode?"),
    # --- standard coverage (sanity: both systems should handle) ---
    dict(id="s1", turns=["Where is my order?"], expect={"track_order"}, tags=["standard"], note=""),
    dict(id="s2", turns=["I forgot my wifi password"], expect={"wifi_help"}, tags=["standard"], note=""),
    dict(id="s3", turns=["Recommend a good restaurant"], expect={"restaurant_suggestion"}, tags=["standard"], note=""),
    dict(id="s4", turns=["Cancel my booking"], expect={"cancel_booking"}, tags=["standard"], note=""),
    dict(id="s5", turns=["Book a flight to Denver"], expect={"book_flight"}, tags=["standard"], note=""),
]

# Expected missing-info questions for the laptop display case (subset match).
EXPECTED_MISSING_INFO = {
    "o2": {"external monitor", "safe mode"},
}
