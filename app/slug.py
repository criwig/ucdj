import random

_ADJECTIVES = [
    "ancient", "blazing", "brave", "calm", "clever", "cosmic", "crimson",
    "dancing", "daring", "dizzy", "electric", "emerald", "epic", "fancy",
    "fierce", "fluffy", "frozen", "funny", "giant", "glowing", "golden",
    "happy", "hidden", "honest", "humble", "hungry", "icy", "invisible",
    "jolly", "joyful", "lazy", "lemon", "lucky", "mad", "magic", "mighty",
    "misty", "mystic", "nervous", "noble", "odd", "orange", "peaceful",
    "pink", "playful", "proud", "purple", "quick", "quiet", "rapid",
    "raving", "red", "regal", "restless", "royal", "rusty", "sacred",
    "shiny", "silent", "silver", "sleepy", "sly", "small", "sneaky",
    "snowy", "spicy", "spooky", "stellar", "strange", "sunny", "swift",
    "tall", "teal", "tiny", "turbo", "ultra", "velvet", "vibrant",
    "wandering", "wild", "windy", "wise", "witty", "woolly", "yellow",
]

_ANIMALS = [
    "albatross", "alpaca", "armadillo", "axolotl", "badger", "bat",
    "beaver", "bison", "boar", "buffalo", "capybara", "cassowary",
    "chameleon", "cheetah", "cobra", "condor", "coyote", "crane",
    "crocodile", "crow", "dingo", "dolphin", "donkey", "dragonfly",
    "eagle", "echidna", "elephant", "falcon", "ferret", "flamingo",
    "fox", "frog", "gecko", "giraffe", "gnu", "gorilla", "hamster",
    "hedgehog", "hippo", "hyena", "ibis", "iguana", "jackal", "jaguar",
    "jellyfish", "kangaroo", "koala", "komodo", "lemur", "leopard",
    "lion", "llama", "lobster", "lynx", "manta", "marmot", "meerkat",
    "mongoose", "moose", "narwhal", "newt", "numbat", "ocelot", "octopus",
    "okapi", "orca", "ostrich", "otter", "owl", "panda", "pangolin",
    "parrot", "peacock", "pelican", "penguin", "platypus", "porcupine",
    "quokka", "rabbit", "raccoon", "raven", "rhino", "salamander",
    "seahorse", "sloth", "snail", "sparrow", "squid", "tapir", "tiger",
    "toucan", "turtle", "vulture", "walrus", "weasel", "wolf", "wombat",
    "wolverine", "yak", "zebra",
]


def generate_slug() -> str:
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_ANIMALS)}"
