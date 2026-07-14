class ContentAnalyzer:
    def __init__(self):
        # Sensitive word list used by the demo moderation logic.
        self.sensitive_words = [
            'trash', 'garbage', 'idiot', 'stupid', 'moron',
            'loser', 'scum', 'go to hell', 'fuck', 'shit', 'bitch', 'damn'
        ]

    def analyze_content(self, content):
        """Check whether the content contains a sensitive word."""
        if not content:
            return False, ""

        content_lower = content.lower()
        for word in self.sensitive_words:
            if word in content_lower:
                return True, f"Message contains a sensitive word: {word}"

        return False, ""

    def filter_content(self, content):
        """Mask sensitive words with asterisks."""
        filtered_content = content
        lowered = filtered_content.lower()
        for word in self.sensitive_words:
            if word in lowered:
                replacement = '*' * len(word)
                filtered_content = filtered_content.replace(word, replacement)
                lowered = filtered_content.lower()
        return filtered_content
