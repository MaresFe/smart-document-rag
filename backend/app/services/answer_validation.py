import re
import unicodedata

from app.services.retrieval import RetrievedChunk


FIXED_NOT_FOUND_ANSWER = (
    "Seçili belgelerde bu bilgi bulunmuyor."
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    flags=re.IGNORECASE,
)

WORD_PATTERN = re.compile(
    r"[^\W_]+",
    flags=re.UNICODE,
)

CITATION_PATTERN = re.compile(
    r"\[\s*(?:Kaynak\s*)?(\d+)\s*\]",
    flags=re.IGNORECASE,
)

TRAILING_GENERIC_NOT_FOUND_PATTERN = re.compile(
    (
        r"\s*Bu ayrıntı seçili belgelerde "
        r"belirtilmiyor\.\s*"
        r"(?:\[Kaynak \d+\])?\s*$"
    ),
    flags=re.IGNORECASE,
)

TURKISH_NUMBER_EQUIVALENTS = {
    "0": "sıfır",
    "1": "bir",
    "2": "iki",
    "3": "üç",
    "4": "dört",
    "5": "beş",
    "6": "altı",
    "7": "yedi",
    "8": "sekiz",
    "9": "dokuz",
    "10": "on",
}

TURKISH_NUMBER_PATTERN = (
    r"(?:\d+|sıfır|bir|iki|üç|dört|beş|altı|"
    r"yedi|sekiz|dokuz|on)"
)

DURATION_PATTERN = re.compile(
    rf"\b(?P<amount>{TURKISH_NUMBER_PATTERN})\s+"
    r"(?P<unit>dakika|saat|gün|hafta|ay|yıl)"
    r"(?P<suffix>\s+boyunca)?\b",
    flags=re.IGNORECASE,
)

RETENTION_QUESTION_PATTERN = re.compile(
    (
        r"^\s*(?P<subject>.+?)\s+ne\s+kadar\s+süre\s+"
        r"(?:saklanır|saklanmaktadır|saklanacak|saklanmalı)"
        r"\s*\??\s*$"
    ),
    flags=re.IGNORECASE,
)

INVALID_RETENTION_ANSWER_PATTERN = re.compile(
    (
        rf"\bBelgenin\s+(?P<duration>{TURKISH_NUMBER_PATTERN}"
        r"\s+(?:dakika|saat|gün|hafta|ay|yıl)"
        r"(?:\s+boyunca)?)\s+saklanmaktadır\b"
    ),
    flags=re.IGNORECASE,
)


ROLE_RULES: dict[
    str,
    dict[str, tuple[str, ...]],
] = {
    "onaylayıcı": {
        "question_patterns": (
            "onaylayıcı",
            "onaylayan",
            "kim onayladı",
            "kim onaylamıştır",
            "kim tarafından onaylandı",
            "kimin onayı",
        ),
        "source_patterns": (
            "onaylayıcı",
            "onaylayan",
            "tarafından onaylandı",
            "onayladı",
            "onaylamıştır",
            "onayıyla",
            "onayı ile",
        ),
    },
    "sorumlu": {
        "question_patterns": (
            "sorumlu kim",
            "sorumlusu kim",
            "sorumlu kişi",
            "sorumlu birim",
        ),
        "source_patterns": (
            "sorumlu:",
            "sorumlusu",
            "sorumlu kişi",
            "sorumlu birim",
            "sorumludur",
        ),
    },
    "sahip": {
        "question_patterns": (
            "sahibi kim",
            "sahibi hangi",
            "kime ait",
            "hangi birime ait",
            "belge sahibi",
            "doküman sahibi",
        ),
        "source_patterns": (
            "belge sahibi",
            "doküman sahibi",
            "sahibidir",
            "sahibi:",
            "aittir",
            "ait olduğu",
        ),
    },
    "hazırlayan": {
        "question_patterns": (
            "hazırlayan kim",
            "kim hazırladı",
            "kim tarafından hazırlandı",
            "hazırlayıcısı",
        ),
        "source_patterns": (
            "hazırlayan",
            "tarafından hazırlandı",
            "hazırladı",
            "hazırlamıştır",
            "hazırlayıcı",
        ),
    },
    "yönetici": {
        "question_patterns": (
            "yöneticisi kim",
            "yönetici kim",
            "hangi yönetici",
        ),
        "source_patterns": (
            "yöneticisi",
            "yönetici:",
            "yönetici olarak",
            "yönetmektedir",
        ),
    },
    "yetkili": {
        "question_patterns": (
            "yetkili kim",
            "yetkilisi kim",
            "yetkili kişi",
            "yetkili birim",
        ),
        "source_patterns": (
            "yetkili kişi",
            "yetkili birim",
            "yetkilisi",
            "yetkilidir",
        ),
    },
    "kurucu": {
        "question_patterns": (
            "kurucusu kim",
            "kurucu kim",
            "kim kurdu",
            "kim tarafından kuruldu",
        ),
        "source_patterns": (
            "kurucusu",
            "kurucu:",
            "tarafından kuruldu",
            "kurmuştur",
        ),
    },
    "işveren": {
        "question_patterns": (
            "işveren kim",
            "işvereni kim",
            "işveren taraf",
        ),
        "source_patterns": (
            "işveren:",
            "işverendir",
            "işveren taraf",
            "işveren olarak",
        ),
    },
    "çalışan": {
        "question_patterns": (
            "çalışan kim",
            "çalışanın adı",
            "hangi çalışan",
        ),
        "source_patterns": (
            "çalışan:",
            "çalışanın adı",
            "çalışandır",
            "çalışan olarak",
        ),
    },
}


def normalize_for_matching(
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        value.casefold(),
    )

    without_combining_marks = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )

    return " ".join(
        without_combining_marks.split()
    )


def find_requested_roles(
    question: str,
) -> list[str]:
    normalized_question = normalize_for_matching(
        question,
    )

    requested_roles: list[str] = []

    for role_name, rule in ROLE_RULES.items():
        question_patterns = rule[
            "question_patterns"
        ]

        if any(
            normalize_for_matching(pattern)
            in normalized_question
            for pattern in question_patterns
        ):
            requested_roles.append(role_name)

    return requested_roles


def source_supports_role(
    role_name: str,
    retrieved_chunks: list[RetrievedChunk],
) -> bool:
    rule = ROLE_RULES[role_name]

    normalized_source_text = normalize_for_matching(
        "\n".join(
            chunk.content
            for chunk in retrieved_chunks
        ),
    )

    return any(
        normalize_for_matching(pattern)
        in normalized_source_text
        for pattern in rule["source_patterns"]
    )


def get_unsupported_requested_role(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str | None:
    requested_roles = find_requested_roles(
        question,
    )

    # Birden fazla rol sorulmuşsa kısmi yanıt
    # ihtimalini LLM değerlendirsin.
    if len(requested_roles) != 1:
        return None

    requested_role = requested_roles[0]

    if source_supports_role(
        role_name=requested_role,
        retrieved_chunks=retrieved_chunks,
    ):
        return None

    return requested_role


def normalize_citations(answer: str) -> str:
    normalized = CITATION_PATTERN.sub(
        lambda match: (
            f"[Kaynak {match.group(1)}]"
        ),
        answer,
    )

    return re.sub(
        r"(\[Kaynak \d+\])(?:\s*\1)+",
        r"\1",
        normalized,
    )


def remove_answer_prefix(answer: str) -> str:
    return re.sub(
        r"^(?:Cevap|Yanıt)\s*:\s*",
        "",
        answer,
        flags=re.IGNORECASE,
    )


def remove_false_not_found_suffix(
    answer: str,
) -> str:
    cleaned = (
        TRAILING_GENERIC_NOT_FOUND_PATTERN.sub(
            "",
            answer,
        ).strip()
    )

    if cleaned and cleaned != answer.strip():
        return cleaned

    return answer


def normalize_fixed_not_found_answer(
    answer: str,
) -> str:
    answer_without_citations = (
        CITATION_PATTERN.sub(
            "",
            answer,
        )
    )

    answer_without_citations = " ".join(
        answer_without_citations.split()
    )

    if (
        answer_without_citations.casefold()
        == FIXED_NOT_FOUND_ANSWER.casefold()
    ):
        return FIXED_NOT_FOUND_ANSWER

    return answer


def collect_source_emails(
    retrieved_chunks: list[RetrievedChunk],
) -> list[str]:
    source_emails: list[str] = []

    for chunk in retrieved_chunks:
        for email in EMAIL_PATTERN.findall(
            chunk.content,
        ):
            if email not in source_emails:
                source_emails.append(email)

    return source_emails


def preserve_exact_email_literals(
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    source_emails = collect_source_emails(
        retrieved_chunks,
    )

    answer_emails = EMAIL_PATTERN.findall(
        answer,
    )

    if len(source_emails) != 1:
        return answer

    expected_email = source_emails[0]
    corrected_answer = answer

    for generated_email in answer_emails:
        if generated_email != expected_email:
            corrected_answer = (
                corrected_answer.replace(
                    generated_email,
                    expected_email,
                )
            )

    return corrected_answer


def normalize_duration_amount(
    value: str,
) -> str:
    normalized = normalize_for_matching(value)

    return normalize_for_matching(
        TURKISH_NUMBER_EQUIVALENTS.get(
            normalized,
            normalized,
        ),
    )


def preserve_exact_duration_literals(
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    source_text = "\n".join(
        chunk.content
        for chunk in retrieved_chunks
    )

    source_durations = list(
        DURATION_PATTERN.finditer(source_text)
    )

    replacements: list[
        tuple[int, int, str]
    ] = []

    for answer_match in DURATION_PATTERN.finditer(
        answer,
    ):
        answer_amount = normalize_duration_amount(
            answer_match.group("amount"),
        )
        answer_unit = normalize_for_matching(
            answer_match.group("unit"),
        )

        matching_source_phrases: dict[
            str,
            str,
        ] = {}

        for source_match in source_durations:
            source_amount = (
                normalize_duration_amount(
                    source_match.group("amount"),
                )
            )
            source_unit = normalize_for_matching(
                source_match.group("unit"),
            )

            if (
                source_amount != answer_amount
                or source_unit != answer_unit
            ):
                continue

            source_phrase = source_match.group(0)
            matching_source_phrases[
                normalize_for_matching(source_phrase)
            ] = source_phrase

        if len(matching_source_phrases) != 1:
            continue

        replacement = next(
            iter(matching_source_phrases.values()),
        )

        if replacement == answer_match.group(0):
            continue

        replacements.append(
            (
                answer_match.start(),
                answer_match.end(),
                replacement,
            ),
        )

    corrected_answer = answer

    for start, end, replacement in reversed(
        replacements,
    ):
        corrected_answer = (
            corrected_answer[:start]
            + replacement
            + corrected_answer[end:]
        )

    return corrected_answer


def correct_retention_subject(
    answer: str,
    question: str,
) -> str:
    question_match = (
        RETENTION_QUESTION_PATTERN.match(question)
    )

    if question_match is None:
        return answer

    subject = " ".join(
        question_match.group("subject").split()
    )

    subject_words = WORD_PATTERN.findall(subject)

    if (
        not subject_words
        or len(subject_words) > 6
        or " ".join(subject_words) != subject
    ):
        return answer

    return INVALID_RETENTION_ANSWER_PATTERN.sub(
        lambda match: (
            f"{subject} {match.group('duration')} "
            "saklanmaktadır"
        ),
        answer,
        count=1,
    )


def is_single_edit_apart(
    left: str,
    right: str,
) -> bool:
    if left == right:
        return False

    if abs(len(left) - len(right)) > 1:
        return False

    if len(left) == len(right):
        difference_count = sum(
            left_character != right_character
            for left_character, right_character
            in zip(left, right, strict=True)
        )

        return difference_count == 1

    shorter, longer = (
        (left, right)
        if len(left) < len(right)
        else (right, left)
    )

    shorter_index = 0
    longer_index = 0
    difference_count = 0

    while (
        shorter_index < len(shorter)
        and longer_index < len(longer)
    ):
        if (
            shorter[shorter_index]
            == longer[longer_index]
        ):
            shorter_index += 1
            longer_index += 1
            continue

        difference_count += 1
        longer_index += 1

        if difference_count > 1:
            return False

    return True


def preserve_near_exact_source_words(
    answer: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    source_text = "\n".join(
        chunk.content
        for chunk in retrieved_chunks
    )

    source_matches = list(
        WORD_PATTERN.finditer(source_text)
    )

    answer_matches = list(
        WORD_PATTERN.finditer(answer)
    )

    if not source_matches or not answer_matches:
        return answer

    source_tokens = [
        match.group(0)
        for match in source_matches
    ]

    normalized_source_tokens = [
        normalize_for_matching(token)
        for token in source_tokens
    ]

    answer_tokens = [
        match.group(0)
        for match in answer_matches
    ]

    normalized_answer_tokens = [
        normalize_for_matching(token)
        for token in answer_tokens
    ]

    source_token_set = set(
        normalized_source_tokens,
    )

    replacements: list[
        tuple[int, int, str]
    ] = []

    for answer_index, answer_match in enumerate(
        answer_matches,
    ):
        answer_token = answer_tokens[answer_index]
        normalized_answer_token = (
            normalized_answer_tokens[answer_index]
        )

        if (
            len(normalized_answer_token) < 4
            or not answer_token[0].isupper()
            or normalized_answer_token
            in source_token_set
        ):
            continue

        previous_answer_token = (
            normalized_answer_tokens[
                answer_index - 1
            ]
            if answer_index > 0
            else None
        )

        next_answer_token = (
            normalized_answer_tokens[
                answer_index + 1
            ]
            if answer_index + 1
            < len(normalized_answer_tokens)
            else None
        )

        candidates: dict[str, str] = {}

        for source_index, source_token in enumerate(
            source_tokens,
        ):
            normalized_source_token = (
                normalized_source_tokens[
                    source_index
                ]
            )

            previous_context_matches = (
                previous_answer_token is not None
                and source_index > 0
                and normalized_source_tokens[
                    source_index - 1
                ]
                == previous_answer_token
            )

            next_context_matches = (
                next_answer_token is not None
                and source_index + 1
                < len(normalized_source_tokens)
                and normalized_source_tokens[
                    source_index + 1
                ]
                == next_answer_token
            )

            if not (
                previous_context_matches
                or next_context_matches
            ):
                continue

            if not is_single_edit_apart(
                normalized_answer_token,
                normalized_source_token,
            ):
                continue

            candidates[
                normalized_source_token
            ] = source_token

        if len(candidates) != 1:
            continue

        replacement = next(
            iter(candidates.values()),
        )

        replacements.append(
            (
                answer_match.start(),
                answer_match.end(),
                replacement,
            ),
        )

    corrected_answer = answer

    for start, end, replacement in reversed(
        replacements,
    ):
        corrected_answer = (
            corrected_answer[:start]
            + replacement
            + corrected_answer[end:]
        )

    return corrected_answer


def clean_generated_answer(
    answer: str,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    unsupported_role = (
        get_unsupported_requested_role(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )
    )

    if unsupported_role is not None:
        return FIXED_NOT_FOUND_ANSWER

    cleaned = answer.strip()

    cleaned = remove_answer_prefix(
        cleaned,
    )

    cleaned = normalize_citations(
        cleaned,
    )

    cleaned = remove_false_not_found_suffix(
        cleaned,
    )

    cleaned = normalize_fixed_not_found_answer(
        cleaned,
    )

    cleaned = preserve_exact_email_literals(
        cleaned,
        retrieved_chunks,
    )

    cleaned = preserve_exact_duration_literals(
        cleaned,
        retrieved_chunks,
    )

    cleaned = correct_retention_subject(
        cleaned,
        question,
    )

    cleaned = preserve_near_exact_source_words(
        cleaned,
        retrieved_chunks,
    )

    return cleaned.strip()
