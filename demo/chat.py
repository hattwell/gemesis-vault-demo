"""Transparent scripted answers, never an LLM or external network call."""
from __future__ import annotations


TOPICS = (
    (
        ("аэролит", "ресурс"),
        "Сценарный ответ: откройте вымышленный справочник «Аэролит 01» и посмотрите связанные сообщения.",
        "url:https://aerolith-01.example/guide",
    ),
    (
        ("навигац", "маршрут"),
        "Сценарный ответ: ресурс «Аэролит 05» связан с темой навигации и несколькими вымышленными авторами.",
        "url:https://aerolith-05.example/guide",
    ),
    (
        ("заметк", "запис"),
        "Сценарный ответ: «Аэролит 02» показывает пример организации вымышленных заметок.",
        "url:https://aerolith-02.example/guide",
    ),
)


def scripted_answer(question: str) -> dict:
    normalized = question.casefold()
    for keywords, reply, resource in TOPICS:
        if any(keyword in normalized for keyword in keywords):
            return {"reply": reply, "refs": [resource], "sources": [],
                    "has_more": False, "scripted": True}
    return {
        "reply": "Это сценарное демо без генерации ИИ. Попробуйте спросить об аэролите, навигации или заметках.",
        "refs": [], "sources": [], "has_more": False, "scripted": True,
    }
