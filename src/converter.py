import re


def make_frontmatter(title: str, source_url: str, obsidian_link: str, published_date: str) -> str:
    # Escape double quotes in title
    safe_title = title.replace('"', '\\"')
    return (
        f'---\n'
        f'title: "{safe_title}"\n'
        f'source: "{source_url}"\n'
        f'author:\n'
        f'  - "{obsidian_link}"\n'
        f'published: {published_date}\n'
        f'---\n\n'
    )


def safe_filename(title: str, author_display: str) -> str:
    """Generate filesystem-safe filename: {title}｜{author}.md"""
    # Remove chars invalid on macOS/Linux filenames
    invalid = re.compile(r'[/\\:*?"<>\x00-\x1f]')
    safe_title = invalid.sub('', title).strip()
    safe_author = invalid.sub('', author_display).strip()
    if safe_author:
        return f"{safe_title}｜{safe_author}.md"
    return f"{safe_title}.md"
