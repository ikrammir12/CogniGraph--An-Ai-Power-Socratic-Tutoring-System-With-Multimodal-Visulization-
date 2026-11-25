"""Rule-based weekly study plan generation; does not require an AI model."""
from datetime import date, datetime, timedelta, timezone


def build_weekly_plan(
    week_start: str,
    quiz_stats: dict,
    weak_topics: list[dict],
    recent_attempts: list[dict],
    minutes_per_day: int = 30,
) -> dict:
    """Build a seven-day plan from recorded learning results."""

    try:
        start = date.fromisoformat(week_start)
    except (TypeError, ValueError) as exc:
        raise ValueError("week_start must be a valid YYYY-MM-DD date.") from exc

    if start.isoformat() != week_start:
        raise ValueError("week_start must be a valid YYYY-MM-DD date.")

    if not isinstance(minutes_per_day, int) or not 15 <= minutes_per_day <= 120:
        raise ValueError("minutes_per_day must be between 15 and 120.")

    weak = [
        item for item in weak_topics
        if str(item.get("topic", "")).strip()
    ][:3]

    # Use recent valid attempts to find course topics when no weak topics
    # have been established yet. Do not infer scores from question wording.
    recent_topic_names = []
    for attempt in recent_attempts:
        name = str(attempt.get("topic") or "").strip()
        if name and name.casefold() not in {
            t.casefold() for t in recent_topic_names
        }:
            recent_topic_names.append(name)
        if len(recent_topic_names) >= 3:
            break

    if weak:
        priority_names = [str(item["topic"]).strip() for item in weak]
        primary = priority_names[0]
        secondary = priority_names[1] if len(priority_names) > 1 else "Course review"
        third = priority_names[2] if len(priority_names) > 2 else secondary

        daily_topics = [
            primary,
            secondary,
            primary,
            third,
            primary,
            "Mixed practice",
            "Weekly recap",
        ]
        plan_mode = "weak-topic-focused"
        explanation = (
            "Sessions prioritize topics currently identified as weak "
            "from recorded quiz attempts."
        )
    elif recent_topic_names:
        primary = recent_topic_names[0]
        secondary = (
            recent_topic_names[1]
            if len(recent_topic_names) > 1 else "Course review"
        )
        third = (
            recent_topic_names[2]
            if len(recent_topic_names) > 2 else secondary
        )
        daily_topics = [
            primary, secondary, primary, third, secondary,
            "Mixed practice", "Weekly recap",
        ]
        plan_mode = "consolidation"
        explanation = (
            "There are recorded quiz topics, but no qualifying weak topics. "
            "This plan consolidates existing topics rather than claiming "
            "a particular weakness."
        )
    else:
        daily_topics = [
            "Course material review",
            "Key concepts",
            "Important terms",
            "Examples from course material",
            "Self-check questions",
            "Mixed review",
            "Weekly recap",
        ]
        plan_mode = "starter"
        explanation = (
            "There is not enough reliable quiz history to prioritize "
            "weak topics. This is a starter plan, not a diagnosis of ability."
        )

    # Use specific weak subtopics where available. Fall back to recorded
    # topic names without claiming an unsupported diagnosis.
    focus_items = []
    if weak:
        for item in weak:
            parent = str(item.get("topic") or "").strip()
            if not parent:
                continue
            subs = [
                str(value).strip()
                for value in (item.get("subtopics") or [])
                if str(value).strip()
            ]
            if subs:
                focus_items.extend((parent, subtopic) for subtopic in subs)
            else:
                focus_items.append((parent, parent))
    elif recent_topic_names:
        focus_items = [(name, name) for name in recent_topic_names]
    else:
        focus_items = [
            (name, name) for name in daily_topics
            if name not in {"Mixed practice", "Weekly recap"}
        ]

    # Remove duplicate parent/focus pairs while preserving priority order.
    focus_items = list(dict.fromkeys(focus_items))
    if not focus_items:
        focus_items = [("Course material review", "Course material review")]

    priority_topics = list(dict.fromkeys(parent for parent, _ in focus_items))
    sessions = []

    for offset in range(7):
        session_date = start + timedelta(days=offset)
        is_recap = offset == 6
        is_mixed = offset == 5

        if is_recap:
            topic = "Weekly recap"
            focus = "What improved and what needs another review"
            duration = min(minutes_per_day, 30)
            session_type = "weekly-recap"
            objective = "Consolidate the week's learning and choose the next priority."
            activities = [
                ("Recall", "Write three ideas you can now explain without notes."),
                ("Check", "Revisit missed questions and verify corrections against the PDF."),
                ("Plan", "Choose one concept to keep practising next week."),
            ]
            success_criteria = "Three takeaways recorded and one next-week priority selected."

        elif is_mixed:
            topic = "Mixed practice"
            focus = ", ".join(priority_topics[:3]) or "Recent course topics"
            duration = minutes_per_day
            session_type = "mixed-practice"
            objective = "Check whether you can apply concepts without relying on topic cues."
            activities = [
                ("Attempt", "Answer a short mixed quiz before revealing explanations."),
                ("Review", "Check every answer against the course material."),
                ("Learn from errors", "Record the two most important gaps to revisit."),
            ]
            success_criteria = "Every incorrect answer has a written correction or follow-up topic."

        else:
            topic, focus = focus_items[offset % len(focus_items)]
            duration = minutes_per_day
            phase = offset % 5

            if phase == 0:
                session_type = "focused-understanding"
                objective = f"Build a clear, source-grounded understanding of {focus}."
                activities = [
                    ("Find the evidence", f"Locate the relevant passage or example for {focus} in the course PDF."),
                    ("Define it", "Write a one-sentence explanation in your own words."),
                    ("Identify details", "Record two supporting details from the source."),
                ]
                success_criteria = "Explain the concept in your own words and identify two supporting details."

            elif phase == 1:
                session_type = "active-recall"
                objective = f"Recall {focus} accurately without depending on the notes."
                activities = [
                    ("Recall", f"Explain {focus} with the PDF closed."),
                    ("Compare", "Identify one related idea and explain how it differs, if the source supports the comparison."),
                    ("Correct", "Reopen the PDF and repair any missing or inaccurate details."),
                ]
                success_criteria = "A closed-book explanation corrected against the source."

            elif phase == 2:
                session_type = "guided-application"
                objective = f"Apply the course material about {focus} to an example."
                activities = [
                    ("Choose an example", "Find an example or worked case in the relevant course passage."),
                    ("Work through it", "Write the steps and explain why each step follows."),
                    ("Check", "Compare your reasoning with the PDF and correct any gap."),
                ]
                success_criteria = "One example worked through with the reasoning explained."

            elif phase == 3:
                session_type = "mistake-review"
                objective = f"Improve your understanding of {focus} by checking likely misconceptions."
                activities = [
                    ("Retry", "Attempt a missed quiz question on this concept if one exists; otherwise write a new question from the PDF."),
                    ("Explain", "State why the correct answer fits the source and why your alternative does not."),
                    ("Record the lesson", "Write one specific mistake to avoid next time."),
                ]
                success_criteria = "One answer justified using the source, with the misconception recorded if applicable."

            else:
                session_type = "self-check"
                objective = f"Check your understanding of {focus} independently."
                activities = [
                    ("Create questions", "Write three short questions answerable from the course passage."),
                    ("Answer from memory", "Answer without looking at your notes."),
                    ("Verify", "Check each answer against the PDF and mark any remaining uncertainty."),
                ]
                success_criteria = "Three questions answered and checked against the source."

        base, remainder = divmod(duration, 3)
        activities = [
            {"title": title, "instruction": instruction,
             "minutes": base + (1 if index < remainder else 0)}
            for index, (title, instruction) in enumerate(activities)
        ]

        sessions.append({
            "date": session_date.isoformat(),
            "day": session_date.strftime("%A"),
            "topic": topic,
            "focus": focus,
            "objective": objective,
            "duration_minutes": duration,
            "session_type": session_type,
            "activities": activities,
            "success_criteria": success_criteria,
            "task": f"{objective} Complete the three activities below.",
        })

    total_attempts = int(quiz_stats.get("attempts", 0) or 0)
    accuracy = quiz_stats.get("accuracy")
    accuracy_percent = (
        round(float(accuracy) * 100, 1)
        if total_attempts and accuracy is not None
        else None
    )

    weak_summary = [
        {
            "topic": str(item["topic"]),
            "attempts": int(item.get("attempts", 0)),
            "accuracy_percent": (
                round(float(item["accuracy"]) * 100, 1)
                if item.get("accuracy") is not None else None
            ),
        }
        for item in weak
    ]

    return {
        "title": "Personalized weekly study plan",
        "week_start": start.isoformat(),
        "week_end": (start + timedelta(days=6)).isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": plan_mode,
        "explanation": explanation,
        "basis": {
            "recorded_attempts_considered": total_attempts,
            "correct": int(quiz_stats.get("correct", 0) or 0),
            "incorrect": int(quiz_stats.get("incorrect", 0) or 0),
            "accuracy_percent": accuracy_percent,
            "weak_topics": weak_summary,
        },
        "sessions": sessions,
    }
