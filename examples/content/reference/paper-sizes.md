---
description: The sizes pages can be printed on.
---

# Paper sizes

The size of pages is set by the `size` property of `@page` rules, with a keyword or two lengths, optionally followed by an orientation (`portrait` or `landscape`).

<div class="landscape" markdown>

## Common sizes

| Name | Width (mm) | Height (mm) | Width (in) | Height (in) | Width (pt) | Height (pt) | CSS keyword |
|---|---|---|---|---|---|---|---|
| A3 | 297 | 420 | 11.69 | 16.54 | 842 | 1191 | `A3` |
| A4 | 210 | 297 | 8.27 | 11.69 | 595 | 842 | `A4` |
| A5 | 148 | 210 | 5.83 | 8.27 | 420 | 595 | `A5` |
| B4 | 250 | 353 | 9.84 | 13.90 | 709 | 1001 | `B4` |
| B5 | 176 | 250 | 6.93 | 9.84 | 499 | 709 | `B5` |
| JIS B4 | 257 | 364 | 10.12 | 14.33 | 729 | 1032 | `JIS-B4` |
| JIS B5 | 182 | 257 | 7.17 | 10.12 | 516 | 729 | `JIS-B5` |
| Letter | 216 | 279 | 8.50 | 11.00 | 612 | 792 | `letter` |
| Legal | 216 | 356 | 8.50 | 14.00 | 612 | 1008 | `legal` |
| Ledger | 279 | 432 | 11.00 | 17.00 | 792 | 1224 | `ledger` |

</div>

## Custom sizes

Any size can be given as a width and a height:

```css
@page {
  size: 6in 9in;
}
```

Documents can mix sizes and orientations: pages are printed one by one, each with its own size.
