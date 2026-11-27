package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/mattn/go-mastodon"
)

type exchange struct {
	path, query string
	status      int
	body        string
}

func fixture(t *testing.T, steps []exchange) (*mastodon.Client, func()) {
	t.Helper()
	requests := make(chan string, len(steps)+10)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		i := len(requests)
		requests <- fmt.Sprintf("%s %s?%s %s", r.Method, r.URL.Path, r.URL.RawQuery, r.Header.Get("Authorization"))
		if i >= len(steps) {
			http.Error(w, "unexpected request", http.StatusInternalServerError)
			return
		}
		step := steps[i]
		w.Header().Set("Content-Type", "application/json")
		// The library reads rel=next as a backward cursor. The monitor must
		// negotiate its own forward min_id on every request instead.
		w.Header().Set("Link", "<"+"https://mastodon.example"+r.URL.Path+"?max_id=2>; rel=\"next\"")
		w.WriteHeader(step.status)
		fmt.Fprint(w, step.body)
	}))
	t.Cleanup(server.Close)
	client := mastodon.NewClient(&mastodon.Config{Server: server.URL, AccessToken: "fixture-token"})
	return client, func() {
		t.Helper()
		close(requests)
		var got, want []string
		for request := range requests {
			got = append(got, request)
		}
		for _, step := range steps {
			want = append(want, "GET "+step.path+"?"+step.query+" Bearer fixture-token")
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("requests = %q, want %q", got, want)
		}
	}
}

func TestOwnBoostsAcrossPagesAndRetry(t *testing.T) {
	ctx := context.Background()
	const accounts = "/api/v1/accounts/verify_credentials"
	const timeline = "/api/v1/accounts/55/statuses"
	client, observed := fixture(t, []exchange{
		{accounts, "", 200, `{"id":"55"}`},
		{timeline, "limit=1", 200, `[{"id":"25","reblog":null}]`},
		{timeline, "limit=2&min_id=25", 200, `[{"id":"28","reblog":{"id":"8","url":"https://mastodon.example/@eli/8"}},{"id":"27","reblog":null}]`},
		{timeline, "limit=2&min_id=28", 503, `{"error":"temporary"}`},
		{timeline, "limit=2&min_id=28", 200, `[{"id":"30","reblog":{"id":"8","url":"https://mastodon.example/@eli/8"}},{"id":"29","reblog":{"id":"9","url":"https://mastodon.example/@mo/9"}}]`},
		{timeline, "limit=2&min_id=30", 200, `[]`},
		{timeline, "limit=2&min_id=30", 200, `[{"id":"31","reblog":null}]`},
		{timeline, "limit=2&min_id=31", 200, `[]`},
	})
	watch, err := startWatch(ctx, client, 2)
	if err != nil {
		t.Fatal(err)
	}
	var got []boost
	emit := func(b boost) error {
		got = append(got, b)
		return nil
	}
	if err := watch.poll(ctx, emit); err == nil {
		t.Fatal("expected the second page request to fail")
	}
	if want := []boost{{"28", "8", "https://mastodon.example/@eli/8"}}; !reflect.DeepEqual(got, want) {
		t.Fatalf("delivered before retry = %#v, want %#v", got, want)
	}
	for range 3 {
		if err := watch.poll(ctx, emit); err != nil {
			t.Fatal(err)
		}
	}
	want := []boost{
		{"28", "8", "https://mastodon.example/@eli/8"},
		{"29", "9", "https://mastodon.example/@mo/9"},
		{"30", "8", "https://mastodon.example/@eli/8"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("boosts = %#v, want %#v", got, want)
	}
	observed()
}

func TestEmptyTimelineAndDeliveryFailureKeepCursor(t *testing.T) {
	ctx := context.Background()
	const timeline = "/api/v1/accounts/55/statuses"
	const page = `[{"id":"3","reblog":{"id":"1","url":"https://mastodon.example/@lee/1"}}]`
	client, observed := fixture(t, []exchange{
		{"/api/v1/accounts/verify_credentials", "", 200, `{"id":"55"}`},
		{timeline, "limit=1", 200, `[]`},
		{timeline, "limit=2&min_id=0", 200, page},
		{timeline, "limit=2&min_id=0", 200, page},
		{timeline, "limit=2&min_id=3", 200, `[]`},
	})
	watch, err := startWatch(ctx, client, 2)
	if err != nil {
		t.Fatal(err)
	}
	failedWrite := errors.New("write failed")
	if err := watch.poll(ctx, func(boost) error { return failedWrite }); !errors.Is(err, failedWrite) {
		t.Fatalf("poll error = %v, want %v", err, failedWrite)
	}
	var got []string
	for range 2 {
		if err := watch.poll(ctx, func(b boost) error {
			got = append(got, string(b.BoostID))
			return nil
		}); err != nil {
			t.Fatal(err)
		}
	}
	if !reflect.DeepEqual(got, []string{"3"}) {
		t.Fatalf("delivered boost IDs = %v", got)
	}
	observed()
}

func TestMalformedPageDoesNotEmitOrAdvance(t *testing.T) {
	ctx := context.Background()
	const timeline = "/api/v1/accounts/55/statuses"
	const query = "limit=3&min_id=25"
	client, observed := fixture(t, []exchange{
		{"/api/v1/accounts/verify_credentials", "", 200, `{"id":"55"}`},
		{timeline, "limit=1", 200, `[{"id":"25","reblog":null}]`},
		{timeline, query, 200, `[{"id":"25","reblog":null},{"id":"24","reblog":{"id":"1"}}]`},
		{timeline, query, 200, `[{"id":"28","reblog":{"id":"1"}},{"id":"27","reblog":null},{"id":"28","reblog":{"id":"1"}}]`},
		{timeline, query, 200, `[{"id":"28","reblog":{"id":""}},{"id":"27","reblog":{"id":"1"}}]`},
		{timeline, query, 200, `[{"id":"29","reblog":{"id":"1"}}]`},
	})
	watch, err := startWatch(ctx, client, 3)
	if err != nil {
		t.Fatal(err)
	}
	var got []boost
	emit := func(b boost) error { got = append(got, b); return nil }
	for range 3 {
		if err := watch.poll(ctx, emit); err == nil {
			t.Fatal("expected malformed page to be rejected")
		}
		if len(got) != 0 || watch.cursor != "25" {
			t.Fatalf("malformed page emitted %v or changed cursor to %s", got, watch.cursor)
		}
	}
	if err := watch.poll(ctx, emit); err != nil {
		t.Fatal(err)
	}
	if want := []boost{{"29", "1", ""}}; !reflect.DeepEqual(got, want) {
		t.Fatalf("boosts = %#v, want %#v", got, want)
	}
	observed()
}
