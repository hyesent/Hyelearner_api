# services/question_index.py
"""
Full question index converted from frontend index.js
All subjects and topics
"""

QUESTION_INDEX = [
    # ========================
    # CORE
    # ========================
    {
        "subject": "Mathematics",
        "completed": True,
        "topics": [
            {"name": "Linear Equations", "file": "core/mathematics/algebra/linear_equations.js", "completed": True},
            {"name": "Quadratic Equations", "file": "core/mathematics/algebra/quadratic_equations.js", "completed": True},
            {"name": "Simultaneous Equations", "file": "core/mathematics/algebra/simultaneous_equations.js", "completed": True},
            {"name": "Inequalities", "file": "core/mathematics/algebra/inequalities.js", "completed": True},
            {"name": "Polynomials", "file": "core/mathematics/algebra/polynomials.js", "completed": True},
            {"name": "Indices and Logarithms", "file": "core/mathematics/algebra/indices_and_logarithms.js", "completed": True},
            {"name": "Sequences and Series", "file": "core/mathematics/algebra/sequences_and_series.js", "completed": True},
            {"name": "Angles", "file": "core/mathematics/geometry/angles.js", "completed": True},
            {"name": "Triangles", "file": "core/mathematics/geometry/triangles.js", "completed": True},
            {"name": "Circles", "file": "core/mathematics/geometry/circles.js", "completed": True},
            {"name": "Polygons", "file": "core/mathematics/geometry/polygons.js", "completed": True},
            {"name": "Mensuration", "file": "core/mathematics/geometry/mensuration.js", "completed": True},
            {"name": "Trigonometric Identities", "file": "core/mathematics/trigonometry/identities.js", "completed": True},
            {"name": "Bearings", "file": "core/mathematics/trigonometry/bearings.js", "completed": True},
            {"name": "Elevations", "file": "core/mathematics/trigonometry/elevations.js", "completed": True},
            {"name": "Trigonometric Graphs", "file": "core/mathematics/trigonometry/graphs.js", "completed": True},
            {"name": "Data Collection", "file": "core/mathematics/statistics/data_collection.js", "completed": True},
            {"name": "Measures of Central Tendency", "file": "core/mathematics/statistics/measures.js", "completed": True},
            {"name": "Charts", "file": "core/mathematics/statistics/charts.js", "completed": True},
            {"name": "Data Interpretation", "file": "core/mathematics/statistics/interpretation.js", "completed": True},
            {"name": "Basic Probability", "file": "core/mathematics/probability/basic_probability.js", "completed": True},
            {"name": "Conditional Probability", "file": "core/mathematics/probability/conditional_probability.js", "completed": True},
            {"name": "Permutations & Combinations", "file": "core/mathematics/probability/permutations_and_combinations.js", "completed": True},
            {"name": "Differentiation", "file": "core/mathematics/calculus/differentiation.js", "completed": True},
            {"name": "Integration", "file": "core/mathematics/calculus/integration.js", "completed": True},
            {"name": "Applications of Calculus", "file": "core/mathematics/calculus/applications.js", "completed": True},
            {"name": "Vector Operations", "file": "core/mathematics/vectors/vector_operations.js", "completed": True},
            {"name": "Position Vectors", "file": "core/mathematics/vectors/position_vectors.js", "completed": True},
            {"name": "Vector Geometry", "file": "core/mathematics/vectors/vector_geometry.js", "completed": True},
            {"name": "Fractions", "file": "core/mathematics/number_system/fractions.js", "completed": True},
            {"name": "Decimals", "file": "core/mathematics/number_system/decimals.js", "completed": True},
            {"name": "Percentages", "file": "core/mathematics/number_system/percentages.js", "completed": True},
            {"name": "Ratios", "file": "core/mathematics/number_system/ratios.js", "completed": True},
            {"name": "Number Bases", "file": "core/mathematics/number_system/bases.js", "completed": True}
        ]
    },
    {
        "subject": "English Language",
        "completed": True,
        "topics": [
            {"name": "Grammar", "file": "core/english_language/grammar.js", "completed": True},
            {"name": "Vocabulary", "file": "core/english_language/vocabulary.js", "completed": True},
            {"name": "Comprehension", "file": "core/english_language/comprehension.js", "completed": True},
            {"name": "Summary", "file": "core/english_language/summary.js", "completed": True},
            {"name": "Lexis and Structure", "file": "core/english_language/lexis_and_structure.js", "completed": True},
            {"name": "Oral English", "file": "core/english_language/oral_english.js", "completed": True},
            {"name": "Essay Writing", "file": "core/english_language/essay_writing.js", "completed": True},
            {"name": "Punctuation", "file": "core/english_language/punctuation.js", "completed": True},
            {"name": "Spelling", "file": "core/english_language/spelling.js", "completed": True},
            {"name": "Idioms", "file": "core/english_language/idioms.js", "completed": True},
            {"name": "Intonation and Stress", "file": "core/english_language/intonation_and_stress.js", "completed": True},
            {"name": "Cloze Passage", "file": "core/english_language/cloze_passage.js", "completed": True},
            {"name": "Synonyms and Antonyms", "file": "core/english_language/synonyms_and_antonyms.js", "completed": True}
        ]
    },

    # ========================
    # SCIENCE
    # ========================
    {
        "subject": "Physics",
        "completed": True,
        "topics": [
            {"name": "Mechanics", "file": "science/physics/mechanics.js", "completed": True},
            {"name": "Heat", "file": "science/physics/heat.js", "completed": True},
            {"name": "Waves", "file": "science/physics/waves.js", "completed": True},
            {"name": "Optics", "file": "science/physics/optics.js", "completed": True},
            {"name": "Electricity", "file": "science/physics/electricity.js", "completed": True},
            {"name": "Magnetism", "file": "science/physics/magnetism.js", "completed": True},
            {"name": "Electronics", "file": "science/physics/electronics.js", "completed": True},
            {"name": "Modern Physics", "file": "science/physics/modern_physics.js", "completed": True},
            {"name": "Measurements", "file": "science/physics/measurements.js", "completed": True}
        ]
    },
    {
        "subject": "Chemistry",
        "completed": True,
        "topics": [
            {"name": "Atomic Structure", "file": "science/chemistry/atomic_structure.js", "completed": True},
            {"name": "Chemical Bonding", "file": "science/chemistry/bonding.js", "completed": True},
            {"name": "Periodic Table", "file": "science/chemistry/periodic_table.js", "completed": True},
            {"name": "Acids and Bases", "file": "science/chemistry/acids_and_bases.js", "completed": True},
            {"name": "Organic Chemistry", "file": "science/chemistry/organic_chemistry.js", "completed": True},
            {"name": "Electrolysis", "file": "science/chemistry/electrolysis.js", "completed": True},
            {"name": "Equilibrium", "file": "science/chemistry/equilibrium.js", "completed": True},
            {"name": "Chemical Calculations", "file": "science/chemistry/calculations.js", "completed": True},
            {"name": "Gases", "file": "science/chemistry/gases.js", "completed": True}
        ]
    },
    {
        "subject": "Biology",
        "completed": True,
        "topics": [
            {"name": "Cell Biology", "file": "science/biology/cell_biology.js", "completed": True},
            {"name": "Genetics", "file": "science/biology/genetics.js", "completed": True},
            {"name": "Ecology", "file": "science/biology/ecology.js", "completed": True},
            {"name": "Evolution", "file": "science/biology/evolution.js", "completed": True},
            {"name": "Human Body", "file": "science/biology/human_body.js", "completed": True},
            {"name": "Plants", "file": "science/biology/plants.js", "completed": True},
            {"name": "Animals", "file": "science/biology/animals.js", "completed": True},
            {"name": "Microorganisms", "file": "science/biology/microorganisms.js", "completed": True}
        ]
    },
    {
        "subject": "Agricultural Science",
        "completed": True,
        "topics": [
            {"name": "Crop Production", "file": "science/agricultural_science/crop_production.js", "completed": True},
            {"name": "Animal Husbandry", "file": "science/agricultural_science/animal_husbandry.js", "completed": True},
            {"name": "Soil Science", "file": "science/agricultural_science/soil_science.js", "completed": True},
            {"name": "Farm Management", "file": "science/agricultural_science/farm_management.js", "completed": True}
        ]
    },
    {
        "subject": "Environmental Science",
        "completed": True,
        "topics": [
            {"name": "Environment", "file": "science/environmental_science/environment.js", "completed": True},
            {"name": "Pollution", "file": "science/environmental_science/pollution.js", "completed": True},
            {"name": "Conservation", "file": "science/environmental_science/conservation.js", "completed": True},
            {"name": "Climate", "file": "science/environmental_science/climate.js", "completed": True}
        ]
    },
    {
        "subject": "Computer Science",
        "completed": True,
        "topics": [
            {"name": "Computer Basics", "file": "science/computer_science/computer_basics.js", "completed": True},
            {"name": "Programming", "file": "science/computer_science/programming.js", "completed": True},
            {"name": "Networking", "file": "science/computer_science/networking.js", "completed": True},
            {"name": "Databases", "file": "science/computer_science/databases.js", "completed": True}
        ]
    },
    {
        "subject": "Information Technology",
        "completed": True,
        "topics": [
            {"name": "Information Technology", "file": "science/information_technology.js", "completed": True}
        ]
    },
    {
        "subject": "Further Mathematics",
        "completed": True,
        "topics": [
            {"name": "Further Mathematics", "file": "science/further_mathematics.js", "completed": True}
        ]
    },
    {
        "subject": "Geography",
        "completed": True,
        "topics": [
            {"name": "Geography", "file": "science/geography.js", "completed": True}
        ]
    },
    {
        "subject": "Technical Drawing",
        "completed": True,
        "topics": [
            {"name": "Technical Drawing", "file": "science/technical_drawing.js", "completed": True}
        ]
    },

    # ========================
    # BUSINESS
    # ========================
    {
        "subject": "Business Studies",
        "completed": True,
        "topics": [
            {"name": "Business Studies", "file": "business/business_studies.js", "completed": True}
        ]
    },
    {
        "subject": "Commerce",
        "completed": True,
        "topics": [
            {"name": "Commerce", "file": "business/commerce.js", "completed": True}
        ]
    },
    {
        "subject": "Economics",
        "completed": True,
        "topics": [
            {"name": "Economics", "file": "business/economics.js", "completed": True}
        ]
    },
    {
        "subject": "Entrepreneurship",
        "completed": True,
        "topics": [
            {"name": "Entrepreneurship", "file": "business/entrepreneurship.js", "completed": True}
        ]
    },
    {
        "subject": "Finance",
        "completed": True,
        "topics": [
            {"name": "Finance", "file": "business/finance.js", "completed": True}
        ]
    },
    {
        "subject": "Marketing",
        "completed": True,
        "topics": [
            {"name": "Marketing", "file": "business/marketing.js", "completed": True}
        ]
    },
    {
        "subject": "Accounting",
        "completed": True,
        "topics": [
            {"name": "Bookkeeping", "file": "business/accounting/bookkeeping.js", "completed": True},
            {"name": "Journals", "file": "business/accounting/journals.js", "completed": True},
            {"name": "Ledgers", "file": "business/accounting/ledgers.js", "completed": True},
            {"name": "Trial Balance", "file": "business/accounting/trial_balance.js", "completed": True},
            {"name": "Financial Statements", "file": "business/accounting/financial_statements.js", "completed": True},
            {"name": "Depreciation", "file": "business/accounting/depreciation.js", "completed": True}
        ]
    },

    # ========================
    # SOCIAL SCIENCES
    # ========================
    {
        "subject": "Civics",
        "completed": True,
        "topics": [
            {"name": "Civics", "file": "social_sciences/civics.js", "completed": True}
        ]
    },
    {
        "subject": "Government",
        "completed": True,
        "topics": [
            {"name": "Government", "file": "social_sciences/government.js", "completed": True}
        ]
    },
    {
        "subject": "History",
        "completed": True,
        "topics": [
            {"name": "History", "file": "social_sciences/history.js", "completed": True}
        ]
    },
    {
        "subject": "Psychology",
        "completed": True,
        "topics": [
            {"name": "Psychology", "file": "social_sciences/psychology.js", "completed": True}
        ]
    },
    {
        "subject": "Sociology",
        "completed": True,
        "topics": [
            {"name": "Sociology", "file": "social_sciences/sociology.js", "completed": True}
        ]
    },

    # ========================
    # HUMANITIES
    # ========================
    {
        "subject": "Literature",
        "completed": True,
        "topics": [
            {"name": "Poetry", "file": "humanities/literature/poetry.js", "completed": True},
            {"name": "Prose", "file": "humanities/literature/prose.js", "completed": True},
            {"name": "Drama", "file": "humanities/literature/drama.js", "completed": True},
            {"name": "Literary Devices", "file": "humanities/literature/literary_devices.js", "completed": True}
        ]
    },
    {
        "subject": "Philosophy",
        "completed": True,
        "topics": [
            {"name": "Philosophy", "file": "humanities/philosophy.js", "completed": True}
        ]
    },
    {
        "subject": "Religious Studies",
        "completed": True,
        "topics": [
            {"name": "Religious Studies", "file": "humanities/religious_studies.js", "completed": True}
        ]
    },
    {
        "subject": "Ethics",
        "completed": True,
        "topics": [
            {"name": "Ethics", "file": "humanities/ethics.js", "completed": True}
        ]
    },

    # ========================
    # LANGUAGES
    # ========================
    {
        "subject": "French",
        "completed": True,
        "topics": [
            {"name": "French", "file": "languages/french.js", "completed": True}
        ]
    },
    {
        "subject": "Spanish",
        "completed": True,
        "topics": [
            {"name": "Spanish", "file": "languages/spanish.js", "completed": True}
        ]
    },
    {
        "subject": "German",
        "completed": True,
        "topics": [
            {"name": "German", "file": "languages/german.js", "completed": True}
        ]
    },
    {
        "subject": "Arabic",
        "completed": True,
        "topics": [
            {"name": "Arabic", "file": "languages/arabic.js", "completed": True}
        ]
    },
    {
        "subject": "Chinese",
        "completed": True,
        "topics": [
            {"name": "Chinese", "file": "languages/chinese.js", "completed": True}
        ]
    },
    {
        "subject": "Portuguese",
        "completed": True,
        "topics": [
            {"name": "Portuguese", "file": "languages/portuguese.js", "completed": True}
        ]
    },
    {
        "subject": "Yoruba",
        "completed": True,
        "topics": [
            {"name": "Yoruba", "file": "languages/yoruba.js", "completed": True}
        ]
    },
    {
        "subject": "Igbo",
        "completed": True,
        "topics": [
            {"name": "Igbo", "file": "languages/igbo.js", "completed": True}
        ]
    },
    {
        "subject": "Hausa",
        "completed": True,
        "topics": [
            {"name": "Hausa", "file": "languages/hausa.js", "completed": True}
        ]
    },
    {
        "subject": "Swahili",
        "completed": True,
        "topics": [
            {"name": "Swahili", "file": "languages/swahili.js", "completed": True}
        ]
    },

    # ========================
    # ARTS
    # ========================
    {
        "subject": "Fine Arts",
        "completed": True,
        "topics": [
            {"name": "Fine Arts", "file": "arts/fine_arts.js", "completed": True}
        ]
    },
    {
        "subject": "Music",
        "completed": True,
        "topics": [
            {"name": "Music", "file": "arts/music.js", "completed": True}
        ]
    },
    {
        "subject": "Drama",
        "completed": True,
        "topics": [
            {"name": "Drama", "file": "arts/drama.js", "completed": True}
        ]
    },
    {
        "subject": "Creative Arts",
        "completed": True,
        "topics": [
            {"name": "Creative Arts", "file": "arts/creative_arts.js", "completed": True}
        ]
    },

    # ========================
    # HEALTH
    # ========================
    {
        "subject": "Health Science",
        "completed": True,
        "topics": [
            {"name": "Health Science", "file": "health/health_science.js", "completed": True}
        ]
    },
    {
        "subject": "Physical Education",
        "completed": True,
        "topics": [
            {"name": "Physical Education", "file": "health/physical_education.js", "completed": True}
        ]
    },
    {
        "subject": "Home Economics",
        "completed": True,
        "topics": [
            {"name": "Home Economics", "file": "health/home_economics.js", "completed": True}
        ]
    },
    {
        "subject": "Food and Nutrition",
        "completed": True,
        "topics": [
            {"name": "Food and Nutrition", "file": "health/food_and_nutrition.js", "completed": True}
        ]
    }
]

# Helper functions
def get_subject_topics(subject_name: str) -> list:
    """Get all topics for a subject"""
    for entry in QUESTION_INDEX:
        if entry["subject"].lower() == subject_name.lower():
            return [topic["name"] for topic in entry["topics"]]
    return []

def get_topic_file(subject_name: str, topic_name: str) -> str:
    """Get the file path for a specific topic"""
    for entry in QUESTION_INDEX:
        if entry["subject"].lower() == subject_name.lower():
            for topic in entry["topics"]:
                if topic["name"].lower() == topic_name.lower():
                    return topic["file"]
    return ""

def get_all_subjects() -> list:
    """Get all subject names"""
    return [entry["subject"] for entry in QUESTION_INDEX]

def is_subject_complete(subject_name: str) -> bool:
    """Check if a subject is marked as complete"""
    for entry in QUESTION_INDEX:
        if entry["subject"].lower() == subject_name.lower():
            return entry.get("completed", False)
    return False
