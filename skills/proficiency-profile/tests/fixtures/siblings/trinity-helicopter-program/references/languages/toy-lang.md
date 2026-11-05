# Language pack: Toy

A fixture pack. Prose that mentions `prose.id` is not a row.

## 1. Basics

| id | concept | nearest analog | trap |
|---|---|---|---|
| `basics.hello` | Hello | print | none |
| `basics.loop-for` | For loops (`for x in y`) | for | off by one |

## 2. Async

| id | concept | nearest analog | trap |
|---|---|---|---|
| `async.task` | Tasks | promises | `async.not-a-row` in a later cell |
| `async.value-task` | Value tasks | none | none |

## 3. Load order

`basics.hello` → `basics.loop-for` → `async.task`

`basics.hello` → `async.task`

## Aliases

`async.valuetask → async.value-task`
`async.old-task -> async.valuetask`
