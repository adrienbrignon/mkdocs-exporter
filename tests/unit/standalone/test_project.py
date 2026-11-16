from pathlib import Path

import pytest

from mkdocs_exporter.standalone.project import ProjectError, find, load


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return path


def test_configuration_files_are_found_like_zensical_does(tmp_path: Path) -> None:
    write(tmp_path / "mkdocs.yml", "site_name: YAML\n")

    assert find(tmp_path) == tmp_path / "mkdocs.yml"

    write(tmp_path / "zensical.toml", "[project]\nsite_name = 'TOML'\n")

    assert find(tmp_path) == tmp_path / "zensical.toml"

    with pytest.raises(ProjectError, match="No configuration file found"):
        find(tmp_path / "elsewhere")


def test_options_come_from_the_plugins_of_zensical_toml(tmp_path: Path) -> None:
    write(tmp_path / "pdf.css", "")
    config = write(
        tmp_path / "zensical.toml",
        "[project]\nsite_name = 'Site'\nsite_url = 'https://example.org/docs/'\n"
        "nav = [{ 'Home' = 'index.md' }]\n\n[project.extra]\nversion = '1.0'\n\n"
        "[project.plugins.exporter.formats.pdf]\nstylesheets = ['pdf.css']\n",
    )

    project = load(config)

    assert project.website.name == "Site"
    assert project.website.url == "https://example.org/docs/"
    assert project.website.extra == {"version": "1.0"}
    assert project.nav == [{"Home": "index.md"}]
    assert project.options.formats.pdf.stylesheets == [str(tmp_path / "pdf.css")]


def test_options_come_from_the_plugins_of_mkdocs_yml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Paths are relative to the configuration file, `!ENV` tags are resolved and
    plugins are listed or mapped."""

    monkeypatch.setenv("EXPORTER_CONCURRENCY", "3")
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "project" / "pdf.css", "")
    config = write(
        tmp_path / "project" / "mkdocs.yml",
        "site_name: Site\nsite_dir: public\nuse_directory_urls: false\n"
        "plugins:\n  - search\n  - exporter:\n      formats:\n        pdf:\n"
        "          concurrency: !ENV EXPORTER_CONCURRENCY\n"
        "          stylesheets: [pdf.css]\n",
    )

    project = load(Path("project/mkdocs.yml"))

    assert project.config_file == config
    assert project.site_dir == tmp_path / "project" / "public"
    assert not project.use_directory_urls
    assert project.options.formats.pdf.concurrency == 3
    assert project.options.formats.pdf.stylesheets == [
        str(tmp_path / "project" / "pdf.css")
    ]

    write(config, "site_name: Site\nplugins:\n  exporter:\n    buttons: []\n")

    assert load(config).options.buttons == []


def test_defaults_without_options(tmp_path: Path) -> None:
    project = load(write(tmp_path / "zensical.toml", "[project]\nsite_name = 'S'\n"))

    assert project.options.formats.pdf.enabled
    assert project.site_dir == tmp_path / "site"
    assert project.docs_dir == tmp_path / "docs"
    assert project.nav is None


def test_invalid_options_are_reported(tmp_path: Path) -> None:
    config = write(
        tmp_path / "zensical.toml",
        "[project]\n[project.plugins.exporter.formats.pdf]\nconcurency = 3\n",
    )

    with pytest.raises(ProjectError, match="Invalid options of the exporter"):
        load(config)


@pytest.mark.parametrize(
    ("plugins", "expected"),
    [
        ("[project.plugins.search]\n", None),
        ("[project.plugins.meta]\n", ".meta.yml"),
        ("[project.plugins.'material/meta']\nmeta_file = '_meta.yml'\n", "_meta.yml"),
        ("[project.plugins.meta]\nenabled = false\n", None),
    ],
)
def test_the_meta_plugin_is_detected(
    tmp_path: Path, plugins: str, expected: str | None
) -> None:
    project = load(write(tmp_path / "zensical.toml", f"[project]\n{plugins}"))

    assert project.meta_file == expected


def test_tags_that_can_not_be_resolved_are_kept(tmp_path: Path) -> None:
    """Python objects of packages that aren't installed (e.g. Material's emoji
    functions) and `!relative` don't prevent reading the configuration, and buttons
    (which the command ignores) aren't validated."""

    write(tmp_path / "base.yml", "site_name: Base\nsite_dir: public\n")
    config = write(
        tmp_path / "mkdocs.yml",
        "INHERIT: base.yml\nsite_name: Site\nmarkdown_extensions:\n"
        "  - pymdownx.emoji:\n      emoji_index: !!python/name:not_installed.twemoji\n"
        "  - pymdownx.snippets:\n      base_path: !relative $config_dir\n"
        "plugins:\n  - exporter:\n      buttons:\n        - title: T\n"
        "          icon: i\n          href: !!python/name:not_installed.href\n",
    )

    project = load(config)
    extensions = project.settings["markdown_extensions"]

    assert project.website.name == "Site"
    assert project.site_dir == tmp_path / "public"
    assert extensions[0]["pymdownx.emoji"]["emoji_index"] == (
        "!!python/name:not_installed.twemoji"
    )
    assert project.ignored == ["buttons"]


def test_malformed_configurations_are_reported(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="Can't read"):
        load(write(tmp_path / "mkdocs.yml", "plugins:\n  - exporter: {formats: [\n"))
    with pytest.raises(ProjectError, match="Can't read"):
        load(write(tmp_path / "zensical.toml", "[project\n"))
