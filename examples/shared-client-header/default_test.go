package sharedheader

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"

	"connectrpc.com/connect/v2"
	"connectrpc.com/connect/v2/connecthttp"
	"google.golang.org/protobuf/types/known/wrapperspb"
)

type httpObservation struct {
	header http.Header
	path   string
}
type observationKey struct{}
type received struct {
	httpObservation
	nativeUserAgent    string
	nativeHasUserAgent bool
}

func TestSharedDefaultOverRealHTTP(t *testing.T) {
	for _, protocol := range []string{"connect", "grpc-web"} {
		t.Run(protocol, func(t *testing.T) {
			var mu sync.Mutex
			observations := make(map[string]received)
			specs := []connect.Spec{
				{Procedure: "/example.v1.FirstService/Echo"},
				{Procedure: "/example.v1.SecondService/Echo"},
			}
			rpc := connect.NewServer()
			for _, spec := range specs {
				rpc.Register(connect.Method{Spec: spec, Handler: func(ctx context.Context, _ connect.Spec, stream connect.ServerStream) error {
					var request wrapperspb.StringValue
					if err := stream.Receive(&request); err != nil {
						return err
					}
					info, ok := connect.CallInfoForServerContext(ctx)
					if !ok {
						return fmt.Errorf("native server CallInfo is missing")
					}
					raw, ok := ctx.Value(observationKey{}).(httpObservation)
					if !ok {
						return fmt.Errorf("actual HTTP observation is missing")
					}
					mu.Lock()
					observations[request.Value] = received{raw, info.RequestHeader().Get("User-Agent"), info.RequestHeader().Has("User-Agent")}
					mu.Unlock()
					return stream.Send(wrapperspb.String(request.Value + " received"))
				}})
			}
			mux := http.NewServeMux()
			connecthttp.Mount(mux, rpc)
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				observed := httpObservation{r.Header.Clone(), r.URL.Path}
				mux.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), observationKey{}, observed)))
			}))
			defer server.Close()
			options := []connecthttp.Option{}
			if protocol == "grpc-web" {
				options = append(options, connecthttp.WithGRPCWeb())
			}
			newClient := func(interceptors ...connect.ClientInterceptor) *connect.Client {
				return connect.NewClient(connecthttp.NewTransport(server.Client(), server.URL, options...), interceptors...)
			}
			call := func(client *connect.Client, spec connect.Spec, id, headerMode string) (received, error) {
				ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
				defer cancel()
				if headerMode != "unset" {
					var info *connect.CallInfo
					ctx, info = connect.NewClientContext(ctx)
					switch headerMode {
					case "custom":
						info.RequestHeader().Set("user-agent", "request-client/2.0")
					case "empty":
						info.RequestHeader().Set("User-Agent", "")
					case "nil":
						info.RequestHeader().SetValues("User-Agent", nil)
					default:
						return received{}, fmt.Errorf("unknown mode %q", headerMode)
					}
				}
				var response wrapperspb.StringValue
				if err := client.CallUnary(ctx, spec, wrapperspb.String(id), &response); err != nil {
					return received{}, err
				}
				if response.Value != id+" received" {
					return received{}, fmt.Errorf("response did not complete for %s", id)
				}
				mu.Lock()
				result, ok := observations[id]
				mu.Unlock()
				if !ok {
					return received{}, fmt.Errorf("HTTP request was not independently recorded for %s", id)
				}
				if result.path != spec.Procedure {
					return received{}, fmt.Errorf("wrong actual RPC path %s", result.path)
				}
				return result, nil
			}
			baseline, err := call(newClient(), specs[0], "native-baseline", "unset")
			if err != nil {
				t.Fatal(err)
			}
			if baseline.header.Get("User-Agent") == "" {
				t.Fatal("native baseline is missing its User-Agent")
			}
			nativeX := baseline.header.Get("X-User-Agent")
			if (protocol == "grpc-web") != (nativeX != "") {
				t.Fatal("native X-User-Agent protocol baseline is wrong")
			}
			shared := DefaultUserAgent("application-client/1.0")
			clients := []*connect.Client{newClient(shared), newClient(shared)}
			verify := func(index int, mode, id string) error {
				got, err := call(clients[index], specs[index], id, mode)
				if err != nil {
					return err
				}
				want := ""
				if mode == "unset" {
					want = "application-client/1.0"
				}
				if mode == "custom" {
					want = "request-client/2.0"
				}
				_, present := got.header["User-Agent"]
				if got.header.Get("User-Agent") != want || present != (want != "") {
					return fmt.Errorf("actual HTTP User-Agent for client%d/%s: got %q present=%v, want %q", index, mode, got.header.Get("User-Agent"), present, want)
				}
				if got.nativeUserAgent != want || got.nativeHasUserAgent != present {
					return fmt.Errorf("native server header disagrees with actual HTTP header")
				}
				if got.header.Get("X-User-Agent") != nativeX {
					return fmt.Errorf("native X-User-Agent changed")
				}
				return nil
			}
			modes := []string{"unset", "custom", "empty", "nil"}
			for i := range clients {
				for _, mode := range modes {
					if err := verify(i, mode, fmt.Sprintf("sequential-%d-%s", i, mode)); err != nil {
						t.Fatal(err)
					}
				}
			}
			var group sync.WaitGroup
			errors := make(chan error, 16)
			for n := 0; n < 16; n++ {
				group.Add(1)
				go func(n int) {
					defer group.Done()
					errors <- verify((n/4)%2, modes[n%len(modes)], fmt.Sprintf("concurrent-%d", n))
				}(n)
			}
			group.Wait()
			close(errors)
			for err := range errors {
				if err != nil {
					t.Error(err)
				}
			}
			mu.Lock()
			count := len(observations)
			mu.Unlock()
			if count != 25 {
				t.Fatalf("expected all 25 completed RPC receipts, got %d", count)
			}
		})
	}
}
