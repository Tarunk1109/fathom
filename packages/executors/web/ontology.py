"""Field ontology mapper — canonical profile keys to whatever an insurer calls them (DL-07).

There is no shared schema across Ontario insurers. One calls it `postal_code`, the next
`postalCode`, the next `zip`, and the label says "Postal code" while the id says `f_1187`. So the
mapper scores each candidate input against a canonical field using every signal the page offers —
label text, name, id, placeholder, aria-label — and returns the best match with a confidence.

Confidence matters downstream: a low-confidence mapping is recorded as a mapping *hypothesis*, the
same way an unevidenced registry edge is (§9.3). It is not silently trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Canonical field -> phrases that identify it. Order is irrelevant; scoring handles precedence.
ONTOLOGY: dict[str, tuple[str, ...]] = {
    "first_name": ("first name", "firstname", "given name", "fname"),
    "last_name": ("last name", "lastname", "surname", "family name", "lname"),
    "date_of_birth": ("date of birth", "birth date", "birthdate", "dob"),
    "address_line_1": ("street address", "address line 1", "address1", "street", "address"),
    "city": ("city", "municipality", "town"),
    "province": ("province", "prov", "state"),
    "postal_code": ("postal code", "postalcode", "postal", "zip code", "zip"),
    "licence_class": ("licence class", "license class", "class of licence", "licence type"),
    "licence_number": ("licence number", "license number", "driver's licence", "drivers licence",
                       "dl number", "licence no"),
    "years_licensed_g": ("years licensed", "years with g", "licensed since"),
    "date_first_licensed": ("date first licensed", "first licensed"),
    "vehicle_year": ("vehicle year", "year of vehicle", "model year", "year"),
    "vehicle_make": ("vehicle make", "make"),
    "vehicle_model": ("vehicle model", "model"),
    "vehicle_trim": ("trim", "series", "body style"),
    "vehicle_ownership": ("owned or leased", "ownership", "own the vehicle"),
    "annual_km": ("annual kilometres", "annual kilometers", "annual km", "kilometres per year",
                  "km per year", "annual mileage", "mileage"),
    "commute_one_way_km": ("commute distance", "one way", "distance to work"),
    "primary_use": ("primary use", "vehicle use", "how is the vehicle used", "use of vehicle"),
    "parking_location": ("where is the vehicle parked", "parking"),
    "marital_status": ("marital status", "married"),
    "gender": ("gender", "sex"),
    "prior_insurance": ("prior insurance", "currently insured", "current insurer"),
    "at_fault_accidents_6y": ("at fault", "at-fault accidents"),
    "convictions_3y": ("convictions", "tickets", "violations"),
    "contact_email": ("email", "e-mail"),
    "contact_phone": ("phone", "telephone", "mobile"),
    "licence_plate": ("licence plate", "license plate", "plate number", "plate"),
    "third_party_liability_limit": ("third party liability", "liability limit", "liability"),
    "collision_deductible": ("collision deductible", "collision"),
    "comprehensive_deductible": ("comprehensive deductible", "comprehensive"),
    "opcf_44r": ("family protection", "opcf 44", "44r"),
    "income_replacement": ("income replacement",),
    "requested_effective_date": ("effective date", "start date", "coverage start"),
}

_NON_WORD = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    return _NON_WORD.sub(" ", (text or "").lower()).strip()


@dataclass(frozen=True)
class FieldMatch:
    canonical: str
    confidence: float
    signal: str

    @property
    def is_hypothesis(self) -> bool:
        """Below this, the mapping is recorded but not trusted without a human eye."""
        return self.confidence < 0.6


def match_field(*, label: str = "", name: str = "", element_id: str = "",
                placeholder: str = "", aria_label: str = "") -> FieldMatch | None:
    """Best canonical field for one input, or None."""
    signals = {
        "label": (normalise(label), 1.0),
        "aria_label": (normalise(aria_label), 0.95),
        "name": (normalise(name), 0.9),
        "id": (normalise(element_id), 0.85),
        "placeholder": (normalise(placeholder), 0.7),
    }

    best: FieldMatch | None = None
    for canonical, phrases in ONTOLOGY.items():
        for phrase in phrases:
            for signal_name, (text, weight) in signals.items():
                if not text:
                    continue
                if text == phrase:
                    score = weight
                elif text.startswith(phrase) or text.endswith(phrase):
                    score = weight * 0.9
                elif phrase in text:
                    score = weight * 0.8
                else:
                    continue
                # Longer phrases are more specific: "collision deductible" beats "collision".
                score *= min(1.0, 0.75 + 0.05 * len(phrase.split()))
                if best is None or score > best.confidence:
                    best = FieldMatch(canonical, round(min(score, 1.0), 3), signal_name)
    return best
