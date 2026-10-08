"""Turning journal text into safe HTML, LiveJournal style.

Entries may use a small set of HTML tags (like LJ did), blank lines become paragraphs,
single line breaks become <br>, and an <lj-cut> tag hides the rest of an entry behind a
"Read more" link on the journal and friends pages. Everything goes through nh3 (a
whitelist HTML sanitizer), so scripts, event handlers and styles can't sneak in.
"""

import re

import nh3
from markupsafe import Markup, escape

ENTRY_TAGS = {
    "a", "b", "strong", "i", "em", "u", "s", "strike", "del", "ins", "sub", "sup", "small", "big",
    "p", "br", "hr", "blockquote", "q", "pre", "code", "ul", "ol", "li", "h3", "h4", "span", "img",
}
ENTRY_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "span": {"title"},
}
COMMENT_TAGS = {"a", "b", "strong", "i", "em", "u", "s", "br", "p", "blockquote", "code"}

CUT_RE = re.compile(r"<lj-cut(?:\s+text=[\"']([^\"']{1,80})[\"'])?\s*/?>", re.IGNORECASE)
BLOCK_RE = re.compile(r"^\s*<(p|ul|ol|blockquote|pre|h3|h4|hr)\b", re.IGNORECASE)


def _paragraphs(text: str) -> str:
    """Blank line => new paragraph, single newline => <br> (skipped inside block tags)."""
    text = text.replace("\r\n", "\n").strip()
    out = []
    for block in re.split(r"\n{2,}", text):
        if BLOCK_RE.match(block):
            out.append(block)
        else:
            out.append("<p>" + block.replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)


def _clean(html: str, tags=ENTRY_TAGS, attrs=ENTRY_ATTRS) -> str:
    return nh3.clean(
        html,
        tags=tags,
        attributes=attrs,
        url_schemes={"http", "https", "mailto"},
        link_rel="nofollow noopener noreferrer ugc",
        strip_comments=True,
    )


def render_entry(content: str, *, url: str | None = None) -> Markup:
    """Full entry, or (when `url` is given) only the part before <lj-cut> plus a link."""
    content = content or ""
    match = CUT_RE.search(content)
    if url and match:
        before = _clean(_paragraphs(content[: match.start()]))
        label = escape(match.group(1) or "Read more…")
        return Markup(f'{before}<p class="lj-cut"><a href="{escape(url)}#cutid1">( {label} )</a></p>')
    content = CUT_RE.sub('<a id="cutid1"></a>', content) if match else content
    return Markup(_clean(_paragraphs(content), attrs={**ENTRY_ATTRS, "a": {"href", "title", "id"}}))


def render_comment(body: str) -> Markup:
    return Markup(_clean(_paragraphs(body), tags=COMMENT_TAGS, attrs={"a": {"href"}}))


def plain_excerpt(content: str, length: int = 160) -> str:
    text = nh3.clean(CUT_RE.sub(" ", content or ""), tags=set())
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= length else text[: length - 1].rsplit(" ", 1)[0] + "…"


# The classic LiveJournal mood list (a selection), with a little emoji each.
MOODS = {
    "accomplished": "🏆", "amused": "😄", "angry": "😠", "annoyed": "😒", "anxious": "😬",
    "artistic": "🎨", "awake": "👀", "bored": "🥱", "busy": "⏳", "calm": "😌", "cheerful": "😊",
    "chill": "🧊", "contemplative": "🤔", "content": "🙂", "crafty": "✂️", "creative": "💡",
    "crushed": "💔", "curious": "🧐", "cynical": "🙄", "determined": "💪", "drained": "🪫",
    "ecstatic": "🤩", "energetic": "⚡", "excited": "🎉", "exhausted": "😵", "geeky": "🤓",
    "giddy": "😆", "grateful": "🙏", "groggy": "😪", "happy": "😃", "hopeful": "🌱", "hungry": "🍕",
    "indescribable": "🌀", "lonely": "🌧️", "loved": "🥰", "mellow": "🎶", "nerdy": "🤓",
    "nostalgic": "📼", "okay": "👌", "optimistic": "🌤️", "productive": "✅", "rushed": "🏃",
    "sad": "😢", "sick": "🤒", "sleepy": "😴", "stressed": "😫", "thoughtful": "💭", "tired": "😩",
    "weird": "👽", "working": "💻",
}


def mood_emoji(mood: str | None) -> str:
    return MOODS.get((mood or "").strip().lower(), "")
