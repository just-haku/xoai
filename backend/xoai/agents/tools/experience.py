"""Experience library tools."""

from xoai.agents.experience import lookup_experience


async def lookup_experience_tool(profile_key: str, query: str) -> str:
    lessons = await lookup_experience(profile_key, query)
    if not lessons:
        return "No prior experience found for this profile."
    return "\n".join(
        f"- {lesson['statement']} (utility={lesson.get('utility_score', 0)})"
        for lesson in lessons
    )
