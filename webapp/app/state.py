import reflex as rx


class GlobalState(rx.State):
    """Global StockSense UI state for the application."""

    # Basic counter example
    count: int = 0

    # A text input example
    user_input: str = ""

    # A list to demonstrate dynamic content
    items: list[str] = []

    def increment(self):
        """Increment the count by 1."""
        self.count += 1

    def decrement(self):
        """Decrement the count by 1."""
        self.count -= 1

    def reset_counter(self):
        """Reset counter to 0."""
        self.count = 0

    def update_input(self, value: str):
        """Update the user input."""
        self.user_input = value

    def add_item(self):
        """Add the current input to the items list."""
        if self.user_input.strip():
            self.items.append(self.user_input.strip())
            self.user_input = ""  # Clear input after adding
