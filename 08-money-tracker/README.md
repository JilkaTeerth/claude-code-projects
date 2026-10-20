# Money

A spending tracker that prices everything in days instead of dollars. Python stdlib server, SQLite, one HTML page, no framework.

## How it works

- One box. I type `chipotle 14`, tap Need, Want, Impulse or Wishlist, and it's logged and dated.
- Before I tap, it answers live: yes, or "not today, but 2 quiet days stacks it", or over.
- The headline is a date: when the money runs out at my real daily rate. Pushing it later is the game.
- Quiet days stack into a visible "you could technically spend" amount. Overspends spread over every day left.
- The wishlist is priced in days against a free alternative.

## Product iteration

It started as a bank synced monthly budget (Plaid). I found that too much work, so it went manual first, three versions in a week, each from my own feedback.

## Details that matter

- A fading two week prior stops day one noise. Without it, one $14 burrito says "broke by November".
- Tested end to end in headless Chromium at desktop and phone widths. That caught a hidden overlay swallowing every click, a phone layout overflowing sideways and a fake month end popup.

## What's in `src/`

`core.py`, `server.py`, `index.html`. The database is not included and the starting pot is a demo value.
