from materialx.emoji import twemoji, to_svg


class HTMLStash:
  """Markdown HTML stash stub."""

  def store(self, str):
    return str


class MarkdownEmoji:
  """Markdown Emojij stub."""

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
    icon = to_svg('twemoji', name, None, None, None, None, None, {}, Markdown())

    if icon is not None:
      return icon.text
  except KeyError:
    return None
