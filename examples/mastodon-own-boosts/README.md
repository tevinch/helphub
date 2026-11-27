# Read your own Mastodon boosts in Go

To find the original post after you boost something in another client, read your account's statuses with go-mastodon. A boost has its own status ID and puts the original post in `status.Reblog`. The original post's ID and URL are in `status.Reblog.ID` and `status.Reblog.URL`.

`StreamingWSUser` follows the home timeline and notifications. Home timeline grouping can suppress a boost when the original post is already near the top of the feed. If you use the stream for other events, check the error from `StreamingWSUser` before reading its channel. [Mastodon streaming API](https://docs.joinmastodon.org/methods/streaming/#user) · [Mastodon 4.7.6 home feed](https://github.com/mastodon/mastodon/blob/v4.7.6/app/lib/feed_manager.rb)

## Run the example

Use Go 1.25 or newer. Use a user access token for your account on its home server. The example reads the account ID and statuses, so grant `read:accounts` and `read:statuses` (or the parent `read` scope). [Account API](https://docs.joinmastodon.org/methods/accounts/#verify_credentials)

In Bash, enter your token without echoing it to the terminal.

```sh
export MASTODON_SERVER=https://mastodon.example
read -r -s MASTODON_TOKEN
export MASTODON_TOKEN
go run .
```

Replace the example server with your home server. Wait for the message that the program is watching, then boost a post from another client. By default the program checks every 30 seconds. Set `-interval 1m` to check once a minute. Each output line contains the boost's wrapper ID and the original post's ID and URL. The URL is empty if the server omits it.

```json
{"boost_id":"30","original_id":"8","original_url":"https://mastodon.example/@eli/8"}
```

The first read establishes a starting point without replaying older boosts. Subsequent requests use the last processed status ID as the `min_id` cursor. For a boost, this means the wrapper ID. Mastodon selects the nearest newer statuses up to the page limit and returns each page newest first. The example walks each page oldest first and also advances past ordinary statuses. If a later page fails, the next check resumes after the statuses already processed. A new boost of the same original post after an unboost gets a new wrapper ID. [Account status pagination](https://docs.joinmastodon.org/methods/accounts/#statuses) · [Status fields](https://docs.joinmastodon.org/entities/Status/#reblog)

This is a view of the account's current statuses. A boost removed before the next read may go unseen. Restarting establishes a new starting point.

## Verify locally

`go test ./...` exercises the go-mastodon v0.0.13 client over local HTTP with synthetic accounts and posts. It checks pagination, chronological output, the original post's ID and URL, retry after an HTTP error, and a second boost of the same post.

## Optional coffee

If this example saved you some time, you're welcome to buy me a coffee. It's entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
