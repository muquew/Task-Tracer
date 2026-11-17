# Third-party notices

Task Tracer's own source and distribution remain subject to [LICENSE](LICENSE).
The following notices apply to bundled third-party assets.

## Task Tracer brand mark

The route, checkpoints and check mark in `fav/task-tracer.svg` are original
Task Tracer artwork covered by [LICENSE](LICENSE). The header, favicon and
installation icons use this artwork. It uses geometric paths and circles,
with no font or third-party icon artwork. `scripts/build_icons.py` generates the
PNG and ICO variants from that source; the maskable and Apple touch icons use
an opaque background.

## Geist

`resources/fonts/Geist-Variable.woff2` is the unmodified variable Geist font
from Vercel's official `geist-font` repository, release v1.9.2, commit
`ef2597cfc42f4797676df105517ccc0a1cfa6569`. It supplies Latin UI text;
Chinese text uses the device's system fonts.

- Project: <https://github.com/vercel/geist-font>
- Source: <https://github.com/vercel/geist-font/blob/ef2597cfc42f4797676df105517ccc0a1cfa6569/fonts/Geist/webfonts/Geist%5Bwght%5D.woff2>
- Font SHA-256: `2ffebe993e969069a9789d15164b7715d42491b5835516c5e3b935d5f81b05f1`
- Copyright 2026 The Geist Project Authors; Copyright (c) 2023 Vercel, in collaboration with basement.studio.
- License: SIL Open Font License 1.1. Both official notices are bundled unchanged as [Geist-OFL.txt](resources/fonts/Geist-OFL.txt) and [Geist-LICENSE.txt](resources/fonts/Geist-LICENSE.txt).

## Tabler Icons

Interface SVG icon definitions in `index.html` use the Tabler Icons outline
collection. These interface icons are separate from the original Task Tracer
brand mark above.

- Project: <https://github.com/tabler/tabler-icons>
- Official SVG sources: <https://github.com/tabler/tabler-icons/tree/main/icons/outline>
- Original source URL pattern: `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg`
- License: MIT, reproduced in full below.

```text
MIT License

Copyright (c) 2020-2026 Paweł Kuna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Tailwind CSS

`resources/workspace.css` includes styles generated with Tailwind CSS 4.3.5.

- Project: <https://github.com/tailwindlabs/tailwindcss>
- License: MIT, reproduced in full below.

```text
MIT License

Copyright (c) Tailwind Labs, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
