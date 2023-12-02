class HTMLStash:
  """Markdown HTML stash stub."""

  def store(self, str):
    """Store function stub."""

    return str


class MarkdownEmoji:
  """Markdown Emojij stub."""

  try:
    from material.extensions.emoji import twemoji
  except ImportError:
    from materialx.emoji import twemoji

  emoji_index = twemoji({}, None)


class Markdown:
  """Markdown stub."""

  htmlStash = HTMLStash()
  inlinePatterns = {
    'emoji': MarkdownEmoji()
  }


def get_icon(name):
  """Gets an icon by its name."""

  if not name.startswith(':'):
    name = ':' + name
  if not name.endswith(':'):
    name = name + ':'

  try:
    from material.extensions.emoji import to_svg
  except ImportError:
    from materialx.emoji import to_svg

  try:
    icon = to_svg('twemoji', name, None, None, None, None, None, {}, Markdown())

    if icon is not None:
      return icon.text
  except KeyError:
    return None
