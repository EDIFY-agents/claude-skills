# The licence, in plain English

EDIFY is released under the **[Functional Source
License](../LICENSE)** (FSL-1.1-Apache-2.0). It is short, and it is worth the two
minutes — but here is the summary, and the summary is binding on nothing. The
[LICENSE](../LICENSE) is the licence.

---

## The short version

| you want to | allowed |
|---|---|
| use EDIFY at work, on commercial code, on client work | ✅ yes |
| use it in a company of any size, in production | ✅ yes |
| read, audit, and modify the source | ✅ yes |
| fork it and run your fork internally | ✅ yes |
| self-host it, embed it in your internal tooling | ✅ yes |
| use it in teaching and research | ✅ yes |
| build and sell a product that *uses* EDIFY internally | ✅ yes |
| offer consulting or professional services around EDIFY | ✅ yes |
| redistribute it, with the licence attached | ✅ yes |
| **sell EDIFY, or a rebranded EDIFY, as a product** | ❌ no |
| **run EDIFY as a paid hosted service** | ❌ no |
| **ship something substantially the same and compete with us** | ❌ no |

If you are a developer or a company that wants to *use* this, everything you want
to do is allowed and you do not need to ask.

The one thing the licence stops is someone taking the work, changing the name, and
selling it back to the same market.

## It becomes Apache 2.0 in two years

Every released version converts to the **Apache License 2.0 on the second
anniversary of its release**, automatically, with a patent grant.

This is irrevocable. We cannot claw it back, and neither can a future owner or
maintainer. A version published today is Apache 2.0 in two years even if this
company is acquired, pivots, or disappears. Release dates are in
[CHANGELOG.md](../CHANGELOG.md), so you can compute the conversion date of any
version without asking us.

## Why not MIT

EDIFY was MIT, and MIT was wrong for it.

The paid tier is five gates in one readable file. Under MIT, anyone could delete
that file, rebrand the result, and sell it — legally. That is not a hypothetical
concern for a tool whose whole commercial layer is deliberately local and
readable, which is a property we [refuse to give up](privacy.md).

The FSL keeps every freedom that matters to a *user* and removes exactly one that
only matters to a *competitor*. We would rather protect the work with a licence
than with obfuscation, a phone-home, or a closed source tree — each of which
would cost you something real.

## Why not AGPL

AGPL would let a competitor build a rival product and comply by publishing
source. It also creates genuine, well-documented anxiety in corporate legal
review — the exact review EDIFY has to pass to be installed on a build server.
FSL is a smaller ask of your lawyers and a bigger obstacle to a competitor.

## Is this open source?

**No, and we will not claim it is.** FSL is *source-available*, not OSI-approved,
because the field-of-use restriction fails the Open Source Definition.

Calling it open source anyway would be the kind of claim this project spends a
lot of effort not making. It is fair for you to weigh that. What you get instead:
the full source, the right to modify and self-host, a dated conversion to a real
open-source licence, and no ability for us to take any of it back.

## The name is separate

The licence covers the code. It does **not** grant rights to the EDIFY name or
logo — see [TRADEMARK.md](../TRADEMARK.md). Fork freely; rename before you ship.

## Contributing

Contributions come in under the same licence, with an explicit grant that lets us
keep the Apache 2.0 conversion promise. Four sentences, in
[CONTRIBUTING.md](../CONTRIBUTING.md).

## Still unsure

Open a [discussion](https://github.com/edify-dev/edify/discussions) and ask. "Can we do X" questions are
answered in public so the next person finds the answer, and the answer is almost
always yes.
