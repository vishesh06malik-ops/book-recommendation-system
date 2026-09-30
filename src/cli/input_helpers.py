"""Safe keyboard input: the program never crashes because of what the user types."""

from __future__ import annotations

from typing import Optional

LINE = "-" * 50


def ask_text(prompt: str) -> str:
    """Read a line of text with surrounding spaces removed."""
    return input(prompt).strip()


def ask_int(prompt: str, low: int, high: int, allow_blank: bool = False) -> Optional[int]:
    """Keep asking until the user types a whole number between low and high.

    Returns None only if allow_blank is True and the user just pressed Enter.
    """
    while True:
        text = ask_text(prompt)
        if not text and allow_blank:
            return None
        try:
            number = int(text)
        except ValueError:
            print(f"  Please enter a number from {low} to {high}.")
            continue
        if low <= number <= high:
            return number
        print(f"  Please enter a number from {low} to {high}.")


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = ask_text(f"{prompt} (y/n): ").lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please type y or n.")


def pause() -> None:
    input("\nPress Enter to continue...")


def heading(text: str) -> None:
    print(f"\n{LINE}\n{text}\n{LINE}")
