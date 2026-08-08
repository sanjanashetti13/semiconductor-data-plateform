"""
AI Manufacturing Copilot — CLI entry point.

Run from the project root:

    python app.py
"""

from __future__ import annotations

from ai.copilot import ask_with_metadata


def main() -> None:
    """Interactive natural-language manufacturing analytics loop."""
    print("=" * 60)
    print("      AI Manufacturing Copilot")
    print("=" * 60)
    print(
        "\nAsk a manufacturing analytics question.\n"
        "Examples:\n"
        "  - Give overall production summary\n"
        "  - Show monthly yield\n"
        "  - Compare Sensor 160 and Sensor 162\n"
        "  - Which month performed best?\n"
        "  - Which month had the lowest yield?\n"
        "  - Give recommendations\n"
        "\nType 'exit' or 'quit' to leave.\n"
    )

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            result = ask_with_metadata(question)
        except Exception as exc:  # noqa: BLE001 — surface errors to CLI users
            print(f"\nError: {exc}\n")
            continue

        print("\n" + "=" * 60)
        print(f"TOOL SELECTED: {result['tool']}")
        print("=" * 60)
        print("\n" + "=" * 60)
        print("AI RESPONSE")
        print("=" * 60)
        print(result["answer"])
        print()


if __name__ == "__main__":
    main()
