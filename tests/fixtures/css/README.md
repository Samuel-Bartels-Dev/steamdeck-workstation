# CSS Loader schema fixtures

The four `steamDeckThemes.Chromahon-*.json` files contain control metadata only
(names, option values, component types/defaults/activators), projected into CSS
Loader's `get_themes` response shape. No upstream CSS or executable code is bundled.
They were read from the authors' published `theme.json` files during v0.2.19 work:

- https://github.com/mugenmono/steamDeckThemes.Chromahon-SM
- https://github.com/mugenmono/steamDeckThemes.Chromahon-QAM
- https://github.com/mugenmono/steamDeckThemes.Chromahon-CM
- https://github.com/mugenmono/steamDeckThemes.Chromahon-Controls

These fixtures validate control discovery against real schemas; they are not an
alternate installation source. Runtime components come exclusively from the Theme
Store via CSS Loader. Other generated fixtures in tests model the published API
and deliberately test failure/state-drift cases.
