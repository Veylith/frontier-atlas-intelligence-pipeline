"""
Unit tests for semantic chunking and DOM pruner (413 Payload Prevention).
"""

from src.llm.chunking import SemanticChunker


def test_dom_pruning_removes_scripts_and_styles():
    raw_html = """
    <html>
        <head>
            <style>.banner { color: red; }</style>
            <script>console.log("tracking pixel");</script>
        </head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <main>
                <h1>Frontier AI Startup</h1>
                <p>Developing next generation autonomous reasoning engines for enterprise.</p>
            </main>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """
    chunker = SemanticChunker()
    clean_text = chunker.clean_and_prune_dom(raw_html)

    assert "Frontier AI Startup" in clean_text
    assert "Developing next generation" in clean_text
    assert "console.log" not in clean_text
    assert "banner" not in clean_text


def test_chunking_large_payload():
    chunker = SemanticChunker(max_chunk_tokens=50, overlap_tokens=10)
    # Generate a long text with multiple paragraphs
    paragraphs = [f"Paragraph {i}: This is dense information about model architecture and performance evaluation." for i in range(20)]
    long_text = "\n\n".join(paragraphs)

    chunks = chunker.chunk_text(long_text)
    assert len(chunks) > 1
    # Ensure every chunk is under max length
    max_chars = chunker.max_chunk_tokens * chunker.chars_per_token
    for ch in chunks:
        assert len(ch) <= max_chars + 100
