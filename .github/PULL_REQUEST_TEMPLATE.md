## What this changes

<!-- One or two sentences. If this needs three paragraphs, it is probably two PRs. -->

## Why

<!-- The failure this fixes, or the task that was hard without it.
     Link the issue or discussion if there is one: Closes #123 -->

## How to see it working

```
# the commands a reviewer runs to watch this do the thing
```

---

- [ ] `pytest` is green
- [ ] `edify check` is no worse than it was on `main`
- [ ] A test fails without this change and passes with it
- [ ] No new runtime dependency (`[project] dependencies` is still `[]`)
- [ ] No new network call outside `edify upgrade` / `edify self update`
- [ ] Commits are signed off (`git commit -s`) — see [CONTRIBUTING.md](../CONTRIBUTING.md)

<!-- If a box is unchecked, say why here rather than deleting it. "No test because
     this is a docs change" is a fine answer and takes one line. -->
