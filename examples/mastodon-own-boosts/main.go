package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/url"
	"os"
	"os/signal"
	"time"

	"github.com/mattn/go-mastodon"
)

type boost struct {
	BoostID     mastodon.ID `json:"boost_id"`
	OriginalID  mastodon.ID `json:"original_id"`
	OriginalURL string      `json:"original_url"`
}

type boostWatch struct {
	client   *mastodon.Client
	account  mastodon.ID
	cursor   mastodon.ID
	pageSize int64
}

func startWatch(ctx context.Context, client *mastodon.Client, pageSize int64) (*boostWatch, error) {
	account, err := client.GetAccountCurrentUser(ctx)
	if err != nil {
		return nil, fmt.Errorf("read account: %w", err)
	}
	if account.ID == "" {
		return nil, errors.New("the server returned an empty account ID")
	}

	statuses, err := client.GetAccountStatuses(ctx, account.ID, &mastodon.Pagination{Limit: 1})
	if err != nil {
		return nil, fmt.Errorf("read latest status: %w", err)
	}
	cursor := mastodon.ID("0")
	if len(statuses) > 0 {
		if statuses[0] == nil || statuses[0].ID == "" {
			return nil, errors.New("the server returned a status without an ID")
		}
		cursor = statuses[0].ID
	}
	return &boostWatch{client: client, account: account.ID, cursor: cursor, pageSize: pageSize}, nil
}

func (w *boostWatch) poll(ctx context.Context, emit func(boost) error) error {
	for {
		// Use a fresh Pagination value because the client updates it from Link.
		page := &mastodon.Pagination{MinID: w.cursor, Limit: w.pageSize}
		statuses, err := w.client.GetAccountStatuses(ctx, w.account, page)
		if err != nil {
			return err
		}
		if err := validatePage(statuses, w.cursor); err != nil {
			return err
		}
		for i := len(statuses) - 1; i >= 0; i-- {
			status := statuses[i]
			if original := status.Reblog; original != nil {
				if err := emit(boost{status.ID, original.ID, original.URL}); err != nil {
					return err
				}
			}
			w.cursor = status.ID
		}
		if int64(len(statuses)) < w.pageSize {
			return nil
		}
	}
}

func validatePage(statuses []*mastodon.Status, cursor mastodon.ID) error {
	seen := map[mastodon.ID]bool{cursor: true}
	for _, status := range statuses {
		if status == nil || status.ID == "" || seen[status.ID] {
			return errors.New("the server returned a missing or repeated status ID")
		}
		if status.Reblog != nil && status.Reblog.ID == "" {
			return errors.New("the server returned a boost without an original status ID")
		}
		seen[status.ID] = true
	}
	return nil
}

func run(ctx context.Context, server, token string, interval time.Duration, output, diagnostics io.Writer) error {
	parsed, err := url.Parse(server)
	if err != nil || parsed.Hostname() == "" || parsed.User != nil {
		return errors.New("set MASTODON_SERVER to your Mastodon server URL")
	}
	loopback := parsed.Scheme == "http" && net.ParseIP(parsed.Hostname()).IsLoopback()
	if parsed.Scheme != "https" && !loopback {
		return errors.New("use HTTPS for your Mastodon server")
	}
	if token == "" {
		return errors.New("set MASTODON_TOKEN to a user access token")
	}
	if interval <= 0 {
		return errors.New("the polling interval must be positive")
	}

	client := mastodon.NewClient(&mastodon.Config{Server: server, AccessToken: token})
	startCtx, cancel := context.WithTimeout(ctx, 20*time.Second)
	watch, err := startWatch(startCtx, client, 40)
	cancel()
	if err != nil {
		return err
	}

	fmt.Fprintln(diagnostics, "Watching for new boosts.")
	encoder := json.NewEncoder(output)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			pollCtx, cancel := context.WithTimeout(ctx, 20*time.Second)
			err := watch.poll(pollCtx, func(b boost) error { return encoder.Encode(b) })
			cancel()
			if err != nil && ctx.Err() == nil {
				fmt.Fprintln(diagnostics, "Could not read new boosts:", err)
			}
		}
	}
}

func main() {
	interval := flag.Duration("interval", 30*time.Second, "time between account status checks")
	flag.Parse()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	if err := run(ctx, os.Getenv("MASTODON_SERVER"), os.Getenv("MASTODON_TOKEN"), *interval, os.Stdout, os.Stderr); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
