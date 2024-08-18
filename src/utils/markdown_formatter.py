
import markdown

class MarkdownFormatter:
    @staticmethod
    def to_markdown(text: str) -> str:
        return markdown.markdown(text)

    @staticmethod
    def from_markdown(markdown_text: str) -> str:
        return markdown_text.replace('#', '').replace('*', '').replace('_', '')
